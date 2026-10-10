"""Entidades principais da operação. Arquivos de foto ficam no storage, nunca no banco."""
from decimal import Decimal

from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.core.validators import MinValueValidator, MaxValueValidator, RegexValidator
from django.db import models
from django.utils import timezone


class PapelUsuario(models.TextChoices):
    DONO = "dono", "Dono"
    ORCAMENTISTA = "orcamentista", "Orçamentista"
    FUNILEIRO = "funileiro", "Funileiro"
    PINTOR = "pintor", "Pintor"
    FINANCEIRO = "financeiro", "Financeiro"


class PerfilUsuario(models.Model):
    usuario = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="perfil_oficina")
    papel = models.CharField(max_length=20, choices=PapelUsuario.choices)
    telefone = models.CharField(max_length=30, blank=True)
    ativo = models.BooleanField(default=True)

    class Meta:
        verbose_name = "perfil de usuário"
        verbose_name_plural = "perfis de usuário"

    def __str__(self):
        return f"{self.usuario.get_full_name() or self.usuario.username} — {self.get_papel_display()}"


class Cliente(models.Model):
    nome = models.CharField(max_length=160)
    telefone = models.CharField(max_length=30)
    email = models.EmailField(blank=True)
    consentimento_dados = models.BooleanField(default=False, verbose_name="consentimento registrado")
    consentimento_em = models.DateTimeField(null=True, blank=True)
    observacao = models.CharField(max_length=300, blank=True)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["nome"]

    def save(self, *args, **kwargs):
        if self.consentimento_dados and not self.consentimento_em:
            self.consentimento_em = timezone.now()
        if not self.consentimento_dados:
            self.consentimento_em = None
        super().save(*args, **kwargs)

    def __str__(self):
        return self.nome


class Seguradora(models.Model):
    nome = models.CharField(max_length=140, unique=True)
    telefone = models.CharField(max_length=30, blank=True)
    email = models.EmailField(blank=True)
    ativa = models.BooleanField(default=True)

    class Meta:
        ordering = ["nome"]
        verbose_name = "seguradora"
        verbose_name_plural = "seguradoras"

    def __str__(self):
        return self.nome


class Veiculo(models.Model):
    cliente = models.ForeignKey(Cliente, on_delete=models.PROTECT, related_name="veiculos")
    placa = models.CharField(max_length=7, unique=True, validators=[RegexValidator(r"^[A-Z]{3}[0-9][A-Z0-9][0-9]{2}$", "Informe uma placa válida, sem hífen.")])
    marca = models.CharField(max_length=60)
    modelo = models.CharField(max_length=80)
    ano = models.PositiveSmallIntegerField(null=True, blank=True, validators=[MinValueValidator(1950), MaxValueValidator(2100)])
    seguradora = models.ForeignKey(Seguradora, on_delete=models.SET_NULL, null=True, blank=True, related_name="veiculos")
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["placa"]

    def save(self, *args, **kwargs):
        self.placa = self.placa.upper().replace("-", "").replace(" ", "")
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.placa} — {self.marca} {self.modelo}"


class StatusOrdemServico(models.TextChoices):
    VISTORIA = "vistoria", "Vistoria"
    ORCAMENTO = "orcamento", "Orçamento"
    AGUARDANDO_APROVACAO = "aguardando_aprovacao", "Aguardando aprovação"
    APROVADO = "aprovado", "Aprovado"
    AGUARDANDO_PECAS = "aguardando_pecas", "Aguardando peças"
    FUNILARIA = "funilaria", "Funilaria"
    PREPARACAO = "preparacao", "Preparação"
    PINTURA = "pintura", "Pintura"
    POLIMENTO = "polimento", "Polimento"
    PRONTA = "pronta", "Pronta para entrega"
    ENTREGUE = "entregue", "Entregue"
    CANCELADA = "cancelada", "Cancelada"


class OrdemServico(models.Model):
    codigo = models.CharField(max_length=20, unique=True, blank=True)
    cliente = models.ForeignKey(Cliente, on_delete=models.PROTECT, related_name="ordens")
    veiculo = models.ForeignKey(Veiculo, on_delete=models.PROTECT, related_name="ordens")
    status = models.CharField(max_length=24, choices=StatusOrdemServico.choices, default=StatusOrdemServico.VISTORIA)
    descricao = models.TextField(blank=True)
    data_abertura = models.DateTimeField(default=timezone.now)
    data_entrega = models.DateTimeField(null=True, blank=True)
    criado_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="ordens_criadas")
    funileiro_responsavel = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="ordens_funilaria")
    pintor_responsavel = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="ordens_pintura")
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-data_abertura"]
        verbose_name = "ordem de serviço"
        verbose_name_plural = "ordens de serviço"

    def clean(self):
        from django.core.exceptions import ValidationError
        if self.cliente_id and self.veiculo_id and self.veiculo.cliente_id != self.cliente_id:
            raise ValidationError({"veiculo": "O veículo deve pertencer ao cliente da ordem."})

    def save(self, *args, **kwargs):
        if not self.codigo:
            hoje = timezone.localdate().strftime("%y%m%d")
            prefixo = f"OS-{hoje}-"
            ultimo = OrdemServico.objects.filter(codigo__startswith=prefixo).order_by("-codigo").first()
            sequencia = int(ultimo.codigo.rsplit("-", 1)[-1]) + 1 if ultimo else 1
            self.codigo = f"{prefixo}{sequencia:03d}"
        super().save(*args, **kwargs)

    def __str__(self):
        return self.codigo


class HistoricoStatusOS(models.Model):
    ordem = models.ForeignKey(OrdemServico, on_delete=models.CASCADE, related_name="historico_status")
    status_anterior = models.CharField(max_length=24, choices=StatusOrdemServico.choices, blank=True)
    status_novo = models.CharField(max_length=24, choices=StatusOrdemServico.choices)
    alterado_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    observacao = models.CharField(max_length=300, blank=True)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["criado_em", "id"]
        verbose_name = "histórico de status"
        verbose_name_plural = "histórico de status"


class FotoVistoria(models.Model):
    class Tipo(models.TextChoices):
        ANTES = "antes", "Antes do serviço"
        DEPOIS = "depois", "Depois do serviço"

    ordem = models.ForeignKey(OrdemServico, on_delete=models.CASCADE, related_name="fotos")
    tipo = models.CharField(max_length=10, choices=Tipo.choices)
    arquivo = models.ImageField(upload_to="vistorias/%Y/%m/")
    descricao = models.CharField(max_length=180, blank=True)
    enviado_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["criado_em"]
        verbose_name = "foto da vistoria"
        verbose_name_plural = "fotos da vistoria"


class StatusOrcamento(models.TextChoices):
    RASCUNHO = "rascunho", "Rascunho"
    ENVIADO = "enviado", "Enviado ao cliente"
    APROVADO = "aprovado", "Aprovado"
    RECUSADO = "recusado", "Recusado"


class Orcamento(models.Model):
    ordem = models.ForeignKey(OrdemServico, on_delete=models.CASCADE, related_name="orcamentos")
    revisao = models.PositiveSmallIntegerField(default=1)
    status = models.CharField(max_length=12, choices=StatusOrcamento.choices, default=StatusOrcamento.RASCUNHO)
    desconto_percentual = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal("0.00"), validators=[MinValueValidator(0), MaxValueValidator(100)])
    validade = models.DateField(null=True, blank=True)
    criado_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="orcamentos_criados")
    atualizado_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="orcamentos_atualizados")
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-revisao"]
        constraints = [models.UniqueConstraint(fields=["ordem", "revisao"], name="uniq_revisao_orcamento_os")]

    def __str__(self):
        return f"{self.ordem.codigo} — revisão {self.revisao}"


class TipoItemOrcamento(models.TextChoices):
    PECA = "peca", "Peça"
    MAO_DE_OBRA = "mao_obra", "Mão de obra"
    HORA_PINTURA = "hora_pintura", "Hora de pintura"
    MATERIAL = "material", "Material"


class ItemOrcamento(models.Model):
    orcamento = models.ForeignKey(Orcamento, on_delete=models.CASCADE, related_name="itens")
    tipo = models.CharField(max_length=16, choices=TipoItemOrcamento.choices)
    descricao = models.CharField(max_length=180)
    quantidade = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal("0.01"))])
    custo_unitario = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"), validators=[MinValueValidator(0)])
    preco_unitario = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(0)])

    class Meta:
        ordering = ["tipo", "descricao"]

    def __str__(self):
        return self.descricao


class TotaisOrcamento(models.Model):
    """Modelo somente leitura da view SQL vw_orcamento_totais."""
    id = models.BigIntegerField(primary_key=True, db_column="orcamento_id")
    subtotal = models.DecimalField(max_digits=14, decimal_places=2)
    custo_total = models.DecimalField(max_digits=14, decimal_places=2)
    desconto_percentual = models.DecimalField(max_digits=5, decimal_places=2)
    valor_desconto = models.DecimalField(max_digits=14, decimal_places=2)
    total_final = models.DecimalField(max_digits=14, decimal_places=2)

    class Meta:
        managed = False
        db_table = "vw_orcamento_totais"
        verbose_name = "total do orçamento"
        verbose_name_plural = "totais dos orçamentos"


class ProdutoEstoque(models.Model):
    class Tipo(models.TextChoices):
        PECA = "peca", "Peça"
        TINTA = "tinta", "Tinta"
        MATERIAL = "material", "Material"

    codigo = models.CharField(max_length=40, unique=True)
    nome = models.CharField(max_length=140)
    tipo = models.CharField(max_length=12, choices=Tipo.choices)
    unidade = models.CharField(max_length=12, default="un")
    quantidade_atual = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    estoque_minimo = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    custo_unitario = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    ativo = models.BooleanField(default=True)

    class Meta:
        ordering = ["nome"]

    def __str__(self):
        return f"{self.codigo} — {self.nome}"


class MovimentoEstoque(models.Model):
    class Tipo(models.TextChoices):
        ENTRADA = "entrada", "Entrada"
        SAIDA = "saida", "Saída"
        AJUSTE = "ajuste", "Ajuste"

    produto = models.ForeignKey(ProdutoEstoque, on_delete=models.PROTECT, related_name="movimentos")
    tipo = models.CharField(max_length=10, choices=Tipo.choices)
    quantidade = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(Decimal("0.01"))])
    custo_unitario = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True, validators=[MinValueValidator(0)])
    ordem = models.ForeignKey(OrdemServico, on_delete=models.SET_NULL, null=True, blank=True, related_name="movimentos_estoque")
    motivo = models.CharField(max_length=180)
    registrado_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-criado_em"]


class Faturamento(models.Model):
    ordem = models.ForeignKey(OrdemServico, on_delete=models.PROTECT, related_name="faturamentos")
    valor_total = models.DecimalField(max_digits=14, decimal_places=2, validators=[MinValueValidator(Decimal("0.01"))])
    emitido_em = models.DateField(default=timezone.localdate)
    observacao = models.CharField(max_length=200, blank=True)
    criado_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-emitido_em"]


class ParcelaReceber(models.Model):
    class Status(models.TextChoices):
        ABERTA = "aberta", "Em aberto"
        PAGA = "paga", "Paga"
        ATRASADA = "atrasada", "Atrasada"

    faturamento = models.ForeignKey(Faturamento, on_delete=models.CASCADE, related_name="parcelas")
    numero = models.PositiveSmallIntegerField()
    valor = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(Decimal("0.01"))])
    vencimento = models.DateField()
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.ABERTA)
    recebido_em = models.DateField(null=True, blank=True)

    class Meta:
        ordering = ["vencimento", "numero"]
        constraints = [models.UniqueConstraint(fields=["faturamento", "numero"], name="uniq_numero_parcela_fat")]


class ContaPagar(models.Model):
    class Status(models.TextChoices):
        ABERTA = "aberta", "Em aberto"
        PAGA = "paga", "Paga"
        ATRASADA = "atrasada", "Atrasada"

    descricao = models.CharField(max_length=180)
    fornecedor = models.CharField(max_length=140, blank=True)
    valor = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(Decimal("0.01"))])
    vencimento = models.DateField()
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.ABERTA)
    pago_em = models.DateField(null=True, blank=True)
    criado_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["vencimento"]


class Comissao(models.Model):
    class Status(models.TextChoices):
        PENDENTE = "pendente", "Pendente"
        PAGA = "paga", "Paga"

    ordem = models.ForeignKey(OrdemServico, on_delete=models.PROTECT, related_name="comissoes")
    profissional = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="comissoes")
    percentual = models.DecimalField(max_digits=5, decimal_places=2, validators=[MinValueValidator(0), MaxValueValidator(100)])
    base_calculo = models.DecimalField(max_digits=14, decimal_places=2, validators=[MinValueValidator(0)])
    valor = models.DecimalField(max_digits=14, decimal_places=2, validators=[MinValueValidator(0)])
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDENTE)
    paga_em = models.DateField(null=True, blank=True)
    criado_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="comissoes_lancadas")
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-criado_em"]


class Auditoria(models.Model):
    ator = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="auditorias")
    acao = models.CharField(max_length=60)
    content_type = models.ForeignKey(ContentType, on_delete=models.PROTECT)
    objeto_id = models.CharField(max_length=64)
    objeto = GenericForeignKey("content_type", "objeto_id")
    antes = models.JSONField(default=dict, blank=True)
    depois = models.JSONField(default=dict, blank=True)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-criado_em"]
        verbose_name = "registro de auditoria"
        verbose_name_plural = "registros de auditoria"
