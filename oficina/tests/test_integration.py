from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase

from oficina.models import Cliente, HistoricoStatusOS, Orcamento, StatusOrcamento, StatusOrdemServico, Veiculo, TotaisOrcamento, ItemOrcamento, TipoItemOrcamento, OrdemServico
from oficina.services.fluxo_os import registrar_abertura_os, transicionar_os


class RegrasPersistidasTests(TestCase):
    def setUp(self):
        self.usuario = get_user_model().objects.create_user(username="dono-teste", password="senha-segura-de-teste")
        self.cliente = Cliente.objects.create(nome="Cliente Teste", telefone="11900001111", consentimento_dados=True)
        self.veiculo = Veiculo.objects.create(cliente=self.cliente, placa="ABC1234", marca="Toyota", modelo="Corolla")
        self.ordem = OrdemServico.objects.create(cliente=self.cliente, veiculo=self.veiculo, criado_por=self.usuario)
        registrar_abertura_os(self.ordem, self.usuario)

    def test_transicao_invalida_nao_altera_status_ou_historico(self):
        with self.assertRaises(ValidationError):
            transicionar_os(ordem_id=self.ordem.pk, status_novo=StatusOrdemServico.PINTURA, ator=self.usuario)
        self.ordem.refresh_from_db()
        self.assertEqual(self.ordem.status, StatusOrdemServico.VISTORIA)
        self.assertEqual(self.ordem.historico_status.count(), 1)

    def test_aprovacao_exige_orcamento_aprovado(self):
        self.ordem.status = StatusOrdemServico.ORCAMENTO
        self.ordem.save(update_fields=["status"])
        with self.assertRaises(ValidationError):
            transicionar_os(ordem_id=self.ordem.pk, status_novo=StatusOrdemServico.APROVADO, ator=self.usuario)
        Orcamento.objects.create(ordem=self.ordem, criado_por=self.usuario, atualizado_por=self.usuario, status=StatusOrcamento.APROVADO)
        transicionar_os(ordem_id=self.ordem.pk, status_novo=StatusOrdemServico.APROVADO, ator=self.usuario)
        self.ordem.refresh_from_db()
        self.assertEqual(self.ordem.status, StatusOrdemServico.APROVADO)

    def test_view_sql_e_fonte_dos_totais(self):
        orcamento = Orcamento.objects.create(ordem=self.ordem, criado_por=self.usuario, atualizado_por=self.usuario, desconto_percentual=Decimal("10"))
        ItemOrcamento.objects.create(orcamento=orcamento, tipo=TipoItemOrcamento.PECA, descricao="Para-choque", quantidade=2, custo_unitario=60, preco_unitario=100)
        ItemOrcamento.objects.create(orcamento=orcamento, tipo=TipoItemOrcamento.HORA_PINTURA, descricao="Pintura", quantidade=2, custo_unitario=30, preco_unitario=75)
        totais = TotaisOrcamento.objects.get(pk=orcamento.pk)
        self.assertEqual(totais.subtotal, Decimal("350.00"))
        self.assertEqual(totais.custo_total, Decimal("180.00"))
        self.assertEqual(totais.valor_desconto, Decimal("35.00"))
        self.assertEqual(totais.total_final, Decimal("315.00"))
