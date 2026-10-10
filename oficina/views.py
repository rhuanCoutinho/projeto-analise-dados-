from datetime import date
from decimal import Decimal
from io import BytesIO

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.db.models import Count, Sum
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST
from reportlab.lib import colors
from reportlab.lib.enums import TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from oficina.forms import (
    ClienteForm, ComissaoForm, ContaPagarForm, FaturamentoForm, FotoVistoriaForm,
    ItemOrcamentoFormSet, MovimentoEstoqueForm, OrcamentoCabecalhoForm,
    OrdemServicoForm, ProdutoEstoqueForm, StatusOSForm, VeiculoForm,
)
from oficina.models import (
    Auditoria, Cliente, Comissao, ContaPagar, Faturamento, FotoVistoria,
    HistoricoStatusOS, MovimentoEstoque, OrdemServico, Orcamento,
    ParcelaReceber, PapelUsuario, ProdutoEstoque, StatusOrcamento, StatusOrdemServico,
    TotaisOrcamento, Veiculo,
)
from oficina.permissions import FINANCEIRO, GESTAO, OPERACAO, TODOS, papel_do_usuario, papeis_permitidos
from oficina.services.auditoria import registrar_auditoria
from oficina.services.estoque import registrar_movimento
from oficina.services.financeiro import emitir_faturamento, gerar_comissao
from oficina.services.fluxo_os import TRANSICOES_VALIDAS, registrar_abertura_os, transicionar_os
from oficina.services.orcamentos import definir_status_orcamento, obter_totais, salvar_itens_orcamento


@papeis_permitidos(*TODOS)
def painel(request):
    abertas = OrdemServico.objects.exclude(status__in=[StatusOrdemServico.ENTREGUE, StatusOrdemServico.CANCELADA])
    por_status = abertas.values("status").annotate(total=Count("id")).order_by("status")
    mes_atual = timezone.localdate().replace(day=1)
    rotulos_status = dict(StatusOrdemServico.choices)
    status_resumo = [{**registro, "rotulo": rotulos_status.get(registro["status"], registro["status"])} for registro in por_status]
    contexto = {
        "ordens_abertas": abertas.count(),
        "aguardando_orcamento": abertas.filter(status__in=[StatusOrdemServico.VISTORIA, StatusOrdemServico.ORCAMENTO, StatusOrdemServico.AGUARDANDO_APROVACAO]).count(),
        "faturamento_mes": Faturamento.objects.filter(emitido_em__gte=mes_atual).aggregate(total=Sum("valor_total"))["total"] or Decimal("0.00"),
        "a_receber": ParcelaReceber.objects.filter(status=ParcelaReceber.Status.ABERTA).aggregate(total=Sum("valor"))["total"] or Decimal("0.00"),
        "a_pagar": ContaPagar.objects.filter(status=ContaPagar.Status.ABERTA).aggregate(total=Sum("valor"))["total"] or Decimal("0.00"),
        "estoque_baixo": ProdutoEstoque.objects.filter(ativo=True, quantidade_atual__lte=models_f("estoque_minimo")).count(),
        "recentes": OrdemServico.objects.select_related("cliente", "veiculo").all()[:8],
        "por_status": status_resumo,
    }
    return render(request, "oficina/painel.html", contexto)


def modelos_f(campo):
    from django.db.models import F
    return F(campo)


@papeis_permitidos(*GESTAO)
def clientes(request):
    termo = request.GET.get("q", "").strip()
    registros = Cliente.objects.all()
    if termo:
        registros = registros.filter(nome__icontains=termo)
    return render(request, "oficina/clientes.html", {"clientes": registros, "termo": termo})


@papeis_permitidos(*GESTAO)
def cliente_novo(request):
    form = ClienteForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        cliente = form.save()
        registrar_auditoria(ator=request.user, objeto=cliente, acao="cliente_criado", depois={"nome": cliente.nome})
        messages.success(request, "Cliente cadastrado.")
        return redirect("clientes")
    return render(request, "oficina/formulario.html", {"form": form, "titulo": "Novo cliente", "voltar": "clientes"})


@papeis_permitidos(*GESTAO)
def veiculos(request):
    return render(request, "oficina/veiculos.html", {"veiculos": Veiculo.objects.select_related("cliente", "seguradora")})


@papeis_permitidos(*GESTAO)
def veiculo_novo(request):
    form = VeiculoForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Veículo cadastrado.")
        return redirect("veiculos")
    return render(request, "oficina/formulario.html", {"form": form, "titulo": "Novo veículo", "voltar": "veiculos"})


@papeis_permitidos(*OPERACAO)
def ordens(request):
    registros = OrdemServico.objects.select_related("cliente", "veiculo")
    papel = papel_do_usuario(request.user)
    if papel == PapelUsuario.FUNILEIRO:
        registros = registros.filter(funileiro_responsavel=request.user)
    elif papel == PapelUsuario.PINTOR:
        registros = registros.filter(pintor_responsavel=request.user)
    return render(request, "oficina/ordens.html", {"ordens": registros})


@papeis_permitidos(*GESTAO)
def ordem_nova(request):
    form = OrdemServicoForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        with transaction.atomic():
            ordem = form.save(commit=False)
            ordem.criado_por = request.user
            ordem.save()
            registrar_abertura_os(ordem, request.user)
            registrar_auditoria(ator=request.user, objeto=ordem, acao="os_criada", depois={"codigo": ordem.codigo, "status": ordem.status})
        messages.success(request, f"Ordem {ordem.codigo} aberta para vistoria.")
        return redirect("ordem_detalhe", pk=ordem.pk)
    return render(request, "oficina/formulario.html", {"form": form, "titulo": "Abrir ordem de serviço", "voltar": "ordens"})


def _ordem_visivel(request, pk):
    ordem = get_object_or_404(OrdemServico.objects.select_related("cliente", "veiculo", "funileiro_responsavel", "pintor_responsavel"), pk=pk)
    papel = papel_do_usuario(request.user)
    if papel == PapelUsuario.FUNILEIRO and ordem.funileiro_responsavel_id != request.user.id:
        raise PermissionDenied
    if papel == PapelUsuario.PINTOR and ordem.pintor_responsavel_id != request.user.id:
        raise PermissionDenied
    return ordem


@papeis_permitidos(*OPERACAO)
def ordem_detalhe(request, pk):
    ordem = _ordem_visivel(request, pk)
    papel = papel_do_usuario(request.user)
    pode_foto = papel in {PapelUsuario.DONO, PapelUsuario.ORCAMENTISTA, PapelUsuario.FUNILEIRO, PapelUsuario.PINTOR}
    status_form = None
    if request.method == "POST" and "mudar_status" in request.POST:
        status_form = StatusOSForm(request.POST)
        if status_form.is_valid():
            destino = status_form.cleaned_data["status"]
            if papel == PapelUsuario.FUNILEIRO and destino not in {StatusOrdemServico.PREPARACAO, StatusOrdemServico.PINTURA}:
                raise PermissionDenied
            if papel == PapelUsuario.PINTOR and destino not in {StatusOrdemServico.PINTURA, StatusOrdemServico.POLIMENTO}:
                raise PermissionDenied
            try:
                transicionar_os(ordem_id=ordem.pk, status_novo=destino, ator=request.user, observacao=status_form.cleaned_data["observacao"])
                messages.success(request, "Etapa da ordem atualizada e registrada no histórico.")
                return redirect("ordem_detalhe", pk=ordem.pk)
            except ValidationError as erro:
                messages.error(request, " ".join(erro.messages))
        else:
            messages.error(request, "Selecione uma próxima etapa válida.")
    destinos = [
        status for status in TRANSICOES_VALIDAS[ordem.status]
        if papel in {PapelUsuario.DONO, PapelUsuario.ORCAMENTISTA}
        or papel == PapelUsuario.FUNILEIRO and status in {StatusOrdemServico.PREPARACAO, StatusOrdemServico.PINTURA}
        or papel == PapelUsuario.PINTOR and status in {StatusOrdemServico.PINTURA, StatusOrdemServico.POLIMENTO}
    ]
    if status_form is None:
        status_form = StatusOSForm(initial={"status": destinos[0] if destinos else ""})
    status_form.fields["status"].choices = [(status, dict(StatusOrdemServico.choices)[status]) for status in destinos]
    if request.method == "POST" and "adicionar_foto" in request.POST:
        if not pode_foto:
            raise PermissionDenied
        foto_form = FotoVistoriaForm(request.POST, request.FILES)
        if foto_form.is_valid():
            foto = foto_form.save(commit=False)
            foto.ordem = ordem
            foto.enviado_por = request.user
            foto.save()
            messages.success(request, "Foto adicionada à vistoria.")
            return redirect("ordem_detalhe", pk=ordem.pk)
    else:
        foto_form = FotoVistoriaForm()
    contexto = {
        "ordem": ordem,
        "historico": ordem.historico_status.select_related("alterado_por"),
        "fotos": ordem.fotos.select_related("enviado_por"),
        "foto_form": foto_form,
        "status_form": status_form,
        "transicoes": destinos,
        "pode_orcar": papel in GESTAO,
    }
    return render(request, "oficina/ordem_detalhe.html", contexto)


@papeis_permitidos(*GESTAO)
def orcamento_editar(request, ordem_id):
    ordem = get_object_or_404(OrdemServico.objects.select_related("cliente", "veiculo"), pk=ordem_id)
    orcamento = ordem.orcamentos.order_by("-revisao").first()
    if orcamento is None:
        orcamento = Orcamento.objects.create(ordem=ordem, criado_por=request.user, atualizado_por=request.user)
    if request.method == "POST" and "mudar_status_orcamento" in request.POST:
        destino = request.POST.get("status_orcamento")
        try:
            with transaction.atomic():
                if destino == StatusOrcamento.APROVADO and not orcamento.itens.exists():
                    raise ValidationError("Inclua itens antes de aprovar o orçamento.")
                definir_status_orcamento(orcamento=orcamento, status=destino, ator=request.user)
                if destino == StatusOrcamento.ENVIADO and ordem.status == StatusOrdemServico.ORCAMENTO:
                    transicionar_os(ordem_id=ordem.pk, status_novo=StatusOrdemServico.AGUARDANDO_APROVACAO, ator=request.user, observacao="Orçamento enviado ao cliente")
                elif destino == StatusOrcamento.APROVADO and ordem.status in {StatusOrdemServico.ORCAMENTO, StatusOrdemServico.AGUARDANDO_APROVACAO}:
                    transicionar_os(ordem_id=ordem.pk, status_novo=StatusOrdemServico.APROVADO, ator=request.user, observacao="Orçamento aprovado")
                elif destino == StatusOrcamento.RECUSADO and ordem.status == StatusOrdemServico.AGUARDANDO_APROVACAO:
                    transicionar_os(ordem_id=ordem.pk, status_novo=StatusOrdemServico.ORCAMENTO, ator=request.user, observacao="Orçamento recusado; revisar valores")
            messages.success(request, "Status do orçamento atualizado.")
        except ValidationError as erro:
            messages.error(request, " ".join(erro.messages))
        return redirect("orcamento_editar", ordem_id=ordem.pk)
    initial = [{key: item[key] for key in ("tipo", "descricao", "quantidade", "custo_unitario", "preco_unitario")} for item in orcamento.itens.values("tipo", "descricao", "quantidade", "custo_unitario", "preco_unitario")]
    form = OrcamentoCabecalhoForm(request.POST or None, instance=orcamento)
    formset = ItemOrcamentoFormSet(request.POST or None, initial=initial, prefix="itens")
    totais = None
    try:
        totais = obter_totais(orcamento)
    except TotaisOrcamento.DoesNotExist:
        pass
    if request.method == "POST" and form.is_valid() and formset.is_valid():
        itens = []
        for item in formset.cleaned_data:
            if item and not item.get("DELETE") and item.get("descricao"):
                itens.append({key: item[key] for key in ("tipo", "descricao", "quantidade", "custo_unitario", "preco_unitario")})
        try:
            salvar_itens_orcamento(orcamento=orcamento, itens=itens, ator=request.user, desconto_percentual=form.cleaned_data["desconto_percentual"], validade=form.cleaned_data["validade"])
            messages.success(request, "Orçamento e auditoria atualizados.")
            return redirect("orcamento_editar", ordem_id=ordem.pk)
        except ValidationError as erro:
            messages.error(request, " ".join(erro.messages))
    return render(request, "oficina/orcamento.html", {"ordem": ordem, "orcamento": orcamento, "form": form, "formset": formset, "totais": totais, "pode_editar": orcamento.status in {StatusOrcamento.RASCUNHO, StatusOrcamento.RECUSADO}})


@papeis_permitidos(*GESTAO)
def orcamento_pdf(request, pk):
    orcamento = get_object_or_404(Orcamento.objects.select_related("ordem__cliente", "ordem__veiculo"), pk=pk)
    totais = obter_totais(orcamento)
    buffer = BytesIO()
    documento = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=18 * mm, leftMargin=18 * mm, topMargin=16 * mm, bottomMargin=16 * mm)
    estilos = getSampleStyleSheet()
    estilos.add(ParagraphStyle(name="SidcarRight", parent=estilos["Normal"], alignment=TA_RIGHT))
    elementos_pdf = [Paragraph("SidCar — Orçamento de reparo", estilos["Title"]), Spacer(1, 6 * mm)]
    ordem = orcamento.ordem
    elementos_pdf.append(Paragraph(f"OS {ordem.codigo} · Revisão {orcamento.revisao}", estilos["Heading2"]))
    elementos_pdf.append(Paragraph(f"Cliente: {ordem.cliente.nome} · Telefone: {ordem.cliente.telefone}", estilos["Normal"]))
    elementos_pdf.append(Paragraph(f"Veículo: {ordem.veiculo.placa} — {ordem.veiculo.marca} {ordem.veiculo.modelo}", estilos["Normal"]))
    elementos_pdf.append(Paragraph(f"Validade: {orcamento.validade or 'não informada'}", estilos["Normal"]))
    elementos_pdf.append(Spacer(1, 5 * mm))
    linhas = [["Tipo", "Descrição", "Qtd.", "Unitário", "Total"]]
    for item in orcamento.itens.all():
        linha_total = item.quantidade * item.preco_unitario
        linhas.append([item.get_tipo_display(), item.descricao, str(item.quantidade), _brl(item.preco_unitario), _brl(linha_total)])
    tabela = Table(linhas, colWidths=[27 * mm, 72 * mm, 18 * mm, 30 * mm, 30 * mm], repeatRows=1)
    tabela.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e8f1f8")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#173b5e")),
        ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#ccd7e2")),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("ALIGN", (2, 1), (-1, -1), "RIGHT"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6), ("TOPPADDING", (0, 0), (-1, -1), 6),
    ]))
    elementos_pdf.append(tabela)
    elementos_pdf.append(Spacer(1, 6 * mm))
    elementos_pdf.append(Paragraph(f"Subtotal: {_brl(totais.subtotal)}", estilos["SidcarRight"]))
    elementos_pdf.append(Paragraph(f"Desconto ({totais.desconto_percentual}%): − {_brl(totais.valor_desconto)}", estilos["SidcarRight"]))
    elementos_pdf.append(Paragraph(f"<b>Total do orçamento: {_brl(totais.total_final)}</b>", estilos["SidcarRight"]))
    documento.build(elementos_pdf)
    resposta = HttpResponse(buffer.getvalue(), content_type="application/pdf")
    resposta["Content-Disposition"] = f'attachment; filename="orcamento-{ordem.codigo}.pdf"'
    return resposta


def _brl(valor):
    texto = f"{Decimal(valor):,.2f}"
    return "R$ " + texto.replace(",", "X").replace(".", ",").replace("X", ".")


@papeis_permitidos(PapelUsuario.DONO, PapelUsuario.FINANCEIRO)
def estoque(request):
    produto_form = ProdutoEstoqueForm(request.POST or None, prefix="produto")
    movimento_form = MovimentoEstoqueForm(request.POST or None, prefix="movimento")
    if request.method == "POST":
        if "salvar_produto" in request.POST and produto_form.is_valid():
            produto = produto_form.save()
            messages.success(request, f"Item {produto.nome} cadastrado. Registre entradas pelo formulário de movimentação.")
            return redirect("estoque")
        if "registrar_movimento" in request.POST and movimento_form.is_valid():
            dados = movimento_form.cleaned_data
            try:
                registrar_movimento(produto_id=dados["produto"].pk, tipo=dados["tipo"], quantidade=dados["quantidade"], custo_unitario=dados["custo_unitario"], ordem=dados["ordem"], motivo=dados["motivo"], usuario=request.user)
                messages.success(request, "Movimentação de estoque registrada.")
                return redirect("estoque")
            except ValidationError as erro:
                messages.error(request, " ".join(erro.messages))
    return render(request, "oficina/estoque.html", {
        "produtos": ProdutoEstoque.objects.filter(ativo=True), "movimentos": MovimentoEstoque.objects.select_related("produto", "registrado_por")[:15],
        "produto_form": produto_form, "movimento_form": movimento_form,
    })


@papeis_permitidos(*FINANCEIRO)
def financeiro(request):
    return render(request, "oficina/financeiro.html", {
        "faturamentos": Faturamento.objects.select_related("ordem")[:20],
        "parcelas": ParcelaReceber.objects.select_related("faturamento__ordem").exclude(status=ParcelaReceber.Status.PAGA)[:30],
        "contas": ContaPagar.objects.exclude(status=ContaPagar.Status.PAGA),
        "comissoes": Comissao.objects.select_related("profissional", "ordem").exclude(status=Comissao.Status.PAGA),
        "faturamento_form": FaturamentoForm(), "conta_form": ContaPagarForm(), "comissao_form": ComissaoForm(),
    })


@papeis_permitidos(*FINANCEIRO)
@require_POST
def financeiro_criar(request):
    acao = request.POST.get("acao")
    if acao == "faturamento":
        form = FaturamentoForm(request.POST)
        if form.is_valid():
            dados = form.cleaned_data
            try:
                faturamento = emitir_faturamento(ordem=dados["ordem"], primeiro_vencimento=dados["primeiro_vencimento"], quantidade_parcelas=dados["quantidade_parcelas"], ator=request.user, observacao=dados["observacao"])
                messages.success(request, f"Faturamento criado com {faturamento.parcelas.count()} parcela(s).")
            except ValidationError as erro:
                messages.error(request, " ".join(erro.messages))
        else:
            messages.error(request, "Confira os dados do faturamento.")
    elif acao == "conta":
        form = ContaPagarForm(request.POST)
        if form.is_valid():
            conta = form.save(commit=False)
            conta.criado_por = request.user
            conta.save()
            messages.success(request, "Conta a pagar registrada.")
        else:
            messages.error(request, "Confira os dados da conta a pagar.")
    elif acao == "comissao":
        form = ComissaoForm(request.POST)
        if form.is_valid():
            try:
                dados = form.cleaned_data
                gerar_comissao(ordem=dados["ordem"], profissional=dados["profissional"], percentual=dados["percentual"], ator=request.user)
                messages.success(request, "Comissão calculada sobre o total do orçamento.")
            except ValidationError as erro:
                messages.error(request, " ".join(erro.messages))
        else:
            messages.error(request, "Confira os dados da comissão.")
    return redirect("financeiro")


@papeis_permitidos(*FINANCEIRO)
@require_POST
def financeiro_pagar(request, tipo, pk):
    hoje = timezone.localdate()
    if tipo == "parcela":
        registro = get_object_or_404(ParcelaReceber, pk=pk)
        registro.status, registro.recebido_em = ParcelaReceber.Status.PAGA, hoje
    elif tipo == "conta":
        registro = get_object_or_404(ContaPagar, pk=pk)
        registro.status, registro.pago_em = ContaPagar.Status.PAGA, hoje
    elif tipo == "comissao":
        registro = get_object_or_404(Comissao, pk=pk)
        registro.status, registro.paga_em = Comissao.Status.PAGA, hoje
    else:
        raise PermissionDenied
    registro.save()
    messages.success(request, "Baixa financeira registrada.")
    return redirect("financeiro")
