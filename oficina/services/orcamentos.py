"""Cálculos e gravação de orçamentos fora da camada HTTP."""
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction

from oficina.models import ItemOrcamento, Orcamento, StatusOrcamento, TotaisOrcamento
from oficina.domain.calculos import calcular_totais, moeda
from oficina.services.auditoria import registrar_auditoria

def obter_totais(orcamento):
    """A view SQL é a fonte de verdade dos valores persistidos."""
    return TotaisOrcamento.objects.get(pk=orcamento.pk)


@transaction.atomic
def salvar_itens_orcamento(*, orcamento, itens, ator, desconto_percentual=None, validade=None):
    orcamento = Orcamento.objects.select_for_update().get(pk=orcamento.pk)
    if orcamento.status not in {StatusOrcamento.RASCUNHO, StatusOrcamento.RECUSADO}:
        raise ValidationError("Reabra o rascunho antes de alterar um orçamento enviado ou aprovado.")
    def itens_para_auditoria():
        return [{chave: str(valor) if isinstance(valor, Decimal) else valor for chave, valor in item.items()}
                for item in orcamento.itens.values("tipo", "descricao", "quantidade", "custo_unitario", "preco_unitario")]

    antes = {
        "desconto_percentual": str(orcamento.desconto_percentual),
        "itens": itens_para_auditoria(),
    }
    if desconto_percentual is not None:
        orcamento.desconto_percentual = desconto_percentual
    orcamento.validade = validade or None
    orcamento.atualizado_por = ator
    orcamento.full_clean()
    orcamento.save(update_fields=["desconto_percentual", "validade", "atualizado_por", "atualizado_em"])
    orcamento.itens.all().delete()
    for item in itens:
        if not item.get("descricao"):
            continue
        linha = ItemOrcamento(orcamento=orcamento, **item)
        linha.full_clean(exclude=["orcamento"])
        linha.save()
    depois = {
        "desconto_percentual": str(orcamento.desconto_percentual),
        "itens": itens_para_auditoria(),
    }
    registrar_auditoria(ator=ator, objeto=orcamento, acao="itens_orcamento_alterados", antes=antes, depois=depois)
    return obter_totais(orcamento)


@transaction.atomic
def definir_status_orcamento(*, orcamento, status, ator):
    if status not in StatusOrcamento.values:
        raise ValidationError("Status de orçamento inválido.")
    transicoes = {
        StatusOrcamento.RASCUNHO: {StatusOrcamento.ENVIADO},
        StatusOrcamento.ENVIADO: {StatusOrcamento.RASCUNHO, StatusOrcamento.APROVADO, StatusOrcamento.RECUSADO},
        StatusOrcamento.RECUSADO: {StatusOrcamento.RASCUNHO},
        StatusOrcamento.APROVADO: set(),
    }
    if status not in transicoes[orcamento.status]:
        raise ValidationError("Esta mudança de status do orçamento não é permitida.")
    anterior = orcamento.status
    revisao_anterior = orcamento.revisao
    orcamento.status = status
    if anterior == StatusOrcamento.RECUSADO and status == StatusOrcamento.RASCUNHO:
        orcamento.revisao += 1
    orcamento.atualizado_por = ator
    orcamento.save(update_fields=["status", "revisao", "atualizado_por", "atualizado_em"])
    registrar_auditoria(ator=ator, objeto=orcamento, acao="status_orcamento_alterado", antes={"status": anterior, "revisao": revisao_anterior}, depois={"status": status, "revisao": orcamento.revisao})
    return orcamento
