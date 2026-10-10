"""Movimentações transacionais de estoque com bloqueio para impedir saldo negativo."""
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction

from oficina.models import MovimentoEstoque, ProdutoEstoque


@transaction.atomic
def registrar_movimento(*, produto_id, tipo, quantidade, usuario, motivo, ordem=None, custo_unitario=None):
    produto = ProdutoEstoque.objects.select_for_update().get(pk=produto_id)
    quantidade = Decimal(str(quantidade))
    if quantidade <= 0:
        raise ValidationError("A quantidade da movimentação deve ser maior que zero.")
    if tipo == MovimentoEstoque.Tipo.SAIDA and quantidade > produto.quantidade_atual:
        raise ValidationError("O estoque não tem quantidade suficiente para esta saída.")
    novo_saldo = produto.quantidade_atual
    if tipo == MovimentoEstoque.Tipo.ENTRADA:
        novo_saldo += quantidade
    elif tipo == MovimentoEstoque.Tipo.SAIDA:
        novo_saldo -= quantidade
    elif tipo == MovimentoEstoque.Tipo.AJUSTE:
        novo_saldo = quantidade
    else:
        raise ValidationError("Tipo de movimentação inválido.")
    movimento = MovimentoEstoque.objects.create(produto=produto, tipo=tipo, quantidade=quantidade, custo_unitario=custo_unitario, ordem=ordem, motivo=motivo, registrado_por=usuario)
    produto.quantidade_atual = novo_saldo
    produto.save(update_fields=["quantidade_atual"])
    return movimento
