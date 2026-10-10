import decimal

import django.contrib.auth.validators
import django.core.validators
import django.db.models.deletion
import django.utils.timezone
from django.conf import settings
from django.db import migrations, models


PAPEIS = [("dono", "Dono"), ("orcamentista", "Orçamentista"), ("funileiro", "Funileiro"), ("pintor", "Pintor"), ("financeiro", "Financeiro")]
STATUS_OS = [("vistoria", "Vistoria"), ("orcamento", "Orçamento"), ("aguardando_aprovacao", "Aguardando aprovação"), ("aprovado", "Aprovado"), ("aguardando_pecas", "Aguardando peças"), ("funilaria", "Funilaria"), ("preparacao", "Preparação"), ("pintura", "Pintura"), ("polimento", "Polimento"), ("pronta", "Pronta para entrega"), ("entregue", "Entregue"), ("cancelada", "Cancelada")]
STATUS_ORCAMENTO = [("rascunho", "Rascunho"), ("enviado", "Enviado ao cliente"), ("aprovado", "Aprovado"), ("recusado", "Recusado")]
TIPOS_ITEM = [("peca", "Peça"), ("mao_obra", "Mão de obra"), ("hora_pintura", "Hora de pintura"), ("material", "Material")]


class Migration(migrations.Migration):
    initial = True
    dependencies = [migrations.swappable_dependency(settings.AUTH_USER_MODEL), ("contenttypes", "0002_remove_content_type_name")]
    operations = [
        migrations.CreateModel(
            name="Cliente",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("nome", models.CharField(max_length=160)), ("telefone", models.CharField(max_length=30)),
                ("email", models.EmailField(blank=True, max_length=254)), ("consentimento_dados", models.BooleanField(default=False, verbose_name="consentimento registrado")),
                ("consentimento_em", models.DateTimeField(blank=True, null=True)), ("observacao", models.CharField(blank=True, max_length=300)), ("criado_em", models.DateTimeField(auto_now_add=True)),
            ], options={"ordering": ["nome"]},
        ),
        migrations.CreateModel(
            name="ProdutoEstoque",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("codigo", models.CharField(max_length=40, unique=True)), ("nome", models.CharField(max_length=140)),
                ("tipo", models.CharField(choices=[("peca", "Peça"), ("tinta", "Tinta"), ("material", "Material")], max_length=12)),
                ("unidade", models.CharField(default="un", max_length=12)),
                ("quantidade_atual", models.DecimalField(decimal_places=2, default=decimal.Decimal("0.00"), max_digits=12)),
                ("estoque_minimo", models.DecimalField(decimal_places=2, default=decimal.Decimal("0.00"), max_digits=12)),
                ("custo_unitario", models.DecimalField(decimal_places=2, default=decimal.Decimal("0.00"), max_digits=12)), ("ativo", models.BooleanField(default=True)),
            ], options={"ordering": ["nome"]},
        ),
        migrations.CreateModel(
            name="Seguradora",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")), ("nome", models.CharField(max_length=140, unique=True)),
                ("telefone", models.CharField(blank=True, max_length=30)), ("email", models.EmailField(blank=True, max_length=254)), ("ativa", models.BooleanField(default=True)),
            ], options={"ordering": ["nome"], "verbose_name": "seguradora", "verbose_name_plural": "seguradoras"},
        ),
        migrations.CreateModel(
            name="PerfilUsuario",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("papel", models.CharField(choices=PAPEIS, max_length=20)), ("telefone", models.CharField(blank=True, max_length=30)), ("ativo", models.BooleanField(default=True)),
                ("usuario", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="perfil_oficina", to=settings.AUTH_USER_MODEL)),
            ], options={"verbose_name": "perfil de usuário", "verbose_name_plural": "perfis de usuário"},
        ),
        migrations.CreateModel(
            name="Veiculo",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("placa", models.CharField(max_length=7, unique=True, validators=[django.core.validators.RegexValidator("^[A-Z]{3}[0-9][A-Z0-9][0-9]{2}$", "Informe uma placa válida, sem hífen.")])),
                ("marca", models.CharField(max_length=60)), ("modelo", models.CharField(max_length=80)),
                ("ano", models.PositiveSmallIntegerField(blank=True, null=True, validators=[django.core.validators.MinValueValidator(1950), django.core.validators.MaxValueValidator(2100)])),
                ("criado_em", models.DateTimeField(auto_now_add=True)),
                ("cliente", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="veiculos", to="oficina.cliente")),
                ("seguradora", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="veiculos", to="oficina.seguradora")),
            ], options={"ordering": ["placa"]},
        ),
        migrations.CreateModel(
            name="OrdemServico",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")), ("codigo", models.CharField(blank=True, max_length=20, unique=True)),
                ("status", models.CharField(choices=STATUS_OS, default="vistoria", max_length=24)), ("descricao", models.TextField(blank=True)),
                ("data_abertura", models.DateTimeField(default=django.utils.timezone.now)), ("data_entrega", models.DateTimeField(blank=True, null=True)),
                ("atualizado_em", models.DateTimeField(auto_now=True)),
                ("cliente", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="ordens", to="oficina.cliente")),
                ("criado_por", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="ordens_criadas", to=settings.AUTH_USER_MODEL)),
                ("funileiro_responsavel", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="ordens_funilaria", to=settings.AUTH_USER_MODEL)),
                ("pintor_responsavel", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="ordens_pintura", to=settings.AUTH_USER_MODEL)),
                ("veiculo", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="ordens", to="oficina.veiculo")),
            ], options={"ordering": ["-data_abertura"], "verbose_name": "ordem de serviço", "verbose_name_plural": "ordens de serviço"},
        ),
        migrations.CreateModel(
            name="FotoVistoria",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("tipo", models.CharField(choices=[("antes", "Antes do serviço"), ("depois", "Depois do serviço")], max_length=10)),
                ("arquivo", models.ImageField(upload_to="vistorias/%Y/%m/")), ("descricao", models.CharField(blank=True, max_length=180)), ("criado_em", models.DateTimeField(auto_now_add=True)),
                ("enviado_por", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to=settings.AUTH_USER_MODEL)),
                ("ordem", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="fotos", to="oficina.ordemservico")),
            ], options={"ordering": ["criado_em"], "verbose_name": "foto da vistoria", "verbose_name_plural": "fotos da vistoria"},
        ),
        migrations.CreateModel(
            name="Orcamento",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")), ("revisao", models.PositiveSmallIntegerField(default=1)),
                ("status", models.CharField(choices=STATUS_ORCAMENTO, default="rascunho", max_length=12)),
                ("desconto_percentual", models.DecimalField(decimal_places=2, default=decimal.Decimal("0.00"), max_digits=5, validators=[django.core.validators.MinValueValidator(0), django.core.validators.MaxValueValidator(100)])),
                ("validade", models.DateField(blank=True, null=True)), ("criado_em", models.DateTimeField(auto_now_add=True)), ("atualizado_em", models.DateTimeField(auto_now=True)),
                ("atualizado_por", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="orcamentos_atualizados", to=settings.AUTH_USER_MODEL)),
                ("criado_por", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="orcamentos_criados", to=settings.AUTH_USER_MODEL)),
                ("ordem", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="orcamentos", to="oficina.ordemservico")),
            ], options={"ordering": ["-revisao"], "constraints": [models.UniqueConstraint(fields=("ordem", "revisao"), name="uniq_revisao_orcamento_os")]},
        ),
        migrations.CreateModel(
            name="ItemOrcamento",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")), ("tipo", models.CharField(choices=TIPOS_ITEM, max_length=16)),
                ("descricao", models.CharField(max_length=180)), ("quantidade", models.DecimalField(decimal_places=2, max_digits=10, validators=[django.core.validators.MinValueValidator(decimal.Decimal("0.01"))])),
                ("custo_unitario", models.DecimalField(decimal_places=2, default=decimal.Decimal("0.00"), max_digits=12, validators=[django.core.validators.MinValueValidator(0)])),
                ("preco_unitario", models.DecimalField(decimal_places=2, max_digits=12, validators=[django.core.validators.MinValueValidator(0)])),
                ("orcamento", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="itens", to="oficina.orcamento")),
            ], options={"ordering": ["tipo", "descricao"]},
        ),
        migrations.CreateModel(
            name="TotaisOrcamento",
            fields=[
                ("id", models.BigIntegerField(db_column="orcamento_id", primary_key=True, serialize=False)),
                ("subtotal", models.DecimalField(decimal_places=2, max_digits=14)), ("custo_total", models.DecimalField(decimal_places=2, max_digits=14)),
                ("desconto_percentual", models.DecimalField(decimal_places=2, max_digits=5)), ("valor_desconto", models.DecimalField(decimal_places=2, max_digits=14)), ("total_final", models.DecimalField(decimal_places=2, max_digits=14)),
            ], options={"managed": False, "db_table": "vw_orcamento_totais", "verbose_name": "total do orçamento", "verbose_name_plural": "totais dos orçamentos"},
        ),
        migrations.CreateModel(
            name="MovimentoEstoque",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("tipo", models.CharField(choices=[("entrada", "Entrada"), ("saida", "Saída"), ("ajuste", "Ajuste")], max_length=10)),
                ("quantidade", models.DecimalField(decimal_places=2, max_digits=12, validators=[django.core.validators.MinValueValidator(decimal.Decimal("0.01"))])),
                ("custo_unitario", models.DecimalField(blank=True, decimal_places=2, max_digits=12, null=True, validators=[django.core.validators.MinValueValidator(0)])),
                ("motivo", models.CharField(max_length=180)), ("criado_em", models.DateTimeField(auto_now_add=True)),
                ("ordem", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="movimentos_estoque", to="oficina.ordemservico")),
                ("produto", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="movimentos", to="oficina.produtoestoque")),
                ("registrado_por", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to=settings.AUTH_USER_MODEL)),
            ], options={"ordering": ["-criado_em"]},
        ),
        migrations.CreateModel(
            name="Faturamento",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")), ("valor_total", models.DecimalField(decimal_places=2, max_digits=14, validators=[django.core.validators.MinValueValidator(decimal.Decimal("0.01"))])),
                ("emitido_em", models.DateField(default=django.utils.timezone.localdate)), ("observacao", models.CharField(blank=True, max_length=200)), ("criado_em", models.DateTimeField(auto_now_add=True)),
                ("criado_por", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to=settings.AUTH_USER_MODEL)),
                ("ordem", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="faturamentos", to="oficina.ordemservico")),
            ], options={"ordering": ["-emitido_em"]},
        ),
        migrations.CreateModel(
            name="ParcelaReceber",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")), ("numero", models.PositiveSmallIntegerField()),
                ("valor", models.DecimalField(decimal_places=2, max_digits=12, validators=[django.core.validators.MinValueValidator(decimal.Decimal("0.01"))])), ("vencimento", models.DateField()),
                ("status", models.CharField(choices=[("aberta", "Em aberto"), ("paga", "Paga"), ("atrasada", "Atrasada")], default="aberta", max_length=10)), ("recebido_em", models.DateField(blank=True, null=True)),
                ("faturamento", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="parcelas", to="oficina.faturamento")),
            ], options={"ordering": ["vencimento", "numero"], "constraints": [models.UniqueConstraint(fields=("faturamento", "numero"), name="uniq_numero_parcela_fat")]},
        ),
        migrations.CreateModel(
            name="ContaPagar",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")), ("descricao", models.CharField(max_length=180)), ("fornecedor", models.CharField(blank=True, max_length=140)),
                ("valor", models.DecimalField(decimal_places=2, max_digits=12, validators=[django.core.validators.MinValueValidator(decimal.Decimal("0.01"))])), ("vencimento", models.DateField()),
                ("status", models.CharField(choices=[("aberta", "Em aberto"), ("paga", "Paga"), ("atrasada", "Atrasada")], default="aberta", max_length=10)), ("pago_em", models.DateField(blank=True, null=True)), ("criado_em", models.DateTimeField(auto_now_add=True)),
                ("criado_por", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to=settings.AUTH_USER_MODEL)),
            ], options={"ordering": ["vencimento"]},
        ),
        migrations.CreateModel(
            name="Comissao",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("percentual", models.DecimalField(decimal_places=2, max_digits=5, validators=[django.core.validators.MinValueValidator(0), django.core.validators.MaxValueValidator(100)])),
                ("base_calculo", models.DecimalField(decimal_places=2, max_digits=14, validators=[django.core.validators.MinValueValidator(0)])), ("valor", models.DecimalField(decimal_places=2, max_digits=14, validators=[django.core.validators.MinValueValidator(0)])),
                ("status", models.CharField(choices=[("pendente", "Pendente"), ("paga", "Paga")], default="pendente", max_length=10)), ("paga_em", models.DateField(blank=True, null=True)), ("criado_em", models.DateTimeField(auto_now_add=True)),
                ("criado_por", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="comissoes_lancadas", to=settings.AUTH_USER_MODEL)),
                ("ordem", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="comissoes", to="oficina.ordemservico")),
                ("profissional", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="comissoes", to=settings.AUTH_USER_MODEL)),
            ], options={"ordering": ["-criado_em"]},
        ),
        migrations.CreateModel(
            name="HistoricoStatusOS",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")), ("status_anterior", models.CharField(blank=True, choices=STATUS_OS, max_length=24)),
                ("status_novo", models.CharField(choices=STATUS_OS, max_length=24)), ("observacao", models.CharField(blank=True, max_length=300)), ("criado_em", models.DateTimeField(auto_now_add=True)),
                ("alterado_por", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to=settings.AUTH_USER_MODEL)),
                ("ordem", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="historico_status", to="oficina.ordemservico")),
            ], options={"ordering": ["criado_em", "id"], "verbose_name": "histórico de status", "verbose_name_plural": "histórico de status"},
        ),
        migrations.CreateModel(
            name="Auditoria",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")), ("acao", models.CharField(max_length=60)), ("objeto_id", models.CharField(max_length=64)),
                ("antes", models.JSONField(blank=True, default=dict)), ("depois", models.JSONField(blank=True, default=dict)), ("criado_em", models.DateTimeField(auto_now_add=True)),
                ("ator", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="auditorias", to=settings.AUTH_USER_MODEL)),
                ("content_type", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to="contenttypes.contenttype")),
            ], options={"ordering": ["-criado_em"], "verbose_name": "registro de auditoria", "verbose_name_plural": "registros de auditoria"},
        ),
    ]
