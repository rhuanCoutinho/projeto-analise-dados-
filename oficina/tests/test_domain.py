import unittest
from decimal import Decimal

from oficina.domain.calculos import calcular_totais
from oficina.domain.transicoes import validar_transicao


class CalculoOrcamentoTests(unittest.TestCase):
    def setUp(self):
        # Peças, mão de obra, horas de pintura e material.
        self.itens = [
            {"tipo": "peca", "quantidade": "2", "preco_unitario": "100.00", "custo_unitario": "60.00"},
            {"tipo": "mao_obra", "quantidade": "3", "preco_unitario": "80.00", "custo_unitario": "35.00"},
            {"tipo": "hora_pintura", "quantidade": "2", "preco_unitario": "75.00", "custo_unitario": "30.00"},
            {"tipo": "material", "quantidade": "1", "preco_unitario": "40.00", "custo_unitario": "20.00"},
        ]

    def test_subtotal_custos_e_desconto(self):
        totais = calcular_totais(self.itens, "10")
        self.assertEqual(totais["subtotal"], Decimal("630.00"))
        self.assertEqual(totais["custo_total"], Decimal("305.00"))
        self.assertEqual(totais["valor_desconto"], Decimal("63.00"))
        self.assertEqual(totais["total_final"], Decimal("567.00"))

    def test_sem_desconto_e_itens_vazios(self):
        self.assertEqual(calcular_totais(self.itens)["total_final"], Decimal("630.00"))
        self.assertEqual(calcular_totais([])["total_final"], Decimal("0.00"))

    def test_desconto_fora_da_faixa_e_rejeitado(self):
        with self.assertRaises(ValueError):
            calcular_totais(self.itens, "100.01")
        with self.assertRaises(ValueError):
            calcular_totais(self.itens, "-1")


class FluxoStatusTests(unittest.TestCase):
    def test_fluxo_principal_e_etapas_opcionais(self):
        caminho = ["vistoria", "orcamento", "aguardando_aprovacao", "aprovado", "aguardando_pecas", "funilaria", "preparacao", "pintura", "polimento", "pronta", "entregue"]
        for atual, novo in zip(caminho, caminho[1:]):
            validar_transicao(atual, novo)

    def test_transicao_invalida_e_rejeitada(self):
        with self.assertRaises(ValueError):
            validar_transicao("vistoria", "pintura")
        with self.assertRaises(ValueError):
            validar_transicao("entregue", "funilaria")

    def test_cancelamento_opcional(self):
        validar_transicao("aguardando_aprovacao", "cancelada")
        with self.assertRaises(ValueError):
            validar_transicao("cancelada", "vistoria")


if __name__ == "__main__":
    unittest.main()
