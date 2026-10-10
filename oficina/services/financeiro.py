"""Operações financeiras calculadas no servidor. Integrações externas ficam fora deste módulo."""
from calendar import monthrange
from datetime import date
from decimal import Decimal, ROUND_HALF_UP

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from oficina.models import Comissao, Faturamento, OrdemServico, ParcelaReceber, StatusOrdemServico, TotaisOrcamento

CENTAVO = Decimal("0.01")


def _somar_mes(data, meses):
    indice = data.month - 1 + meses
    ano = data.year + indice // 12
    mes = indice % 12 + 1
    dia = min(data.day, monthrange(ano, mes)[1])
    return date(ano, mes, dia)


@transaction.atomic
def emitir_faturamento(*, ordem, primeiro_vencimento, quantidade_parcelas, ator, observacao=""):
    if ordem.status != StatusOrdemServico.ENTREGUE:
        raise ValidationError("Só é possível faturar uma ordem entregue.")
    orcamento = ordem.orcamentos.order_by("-revisao").first()
    if not orcamento:
        raise ValidationError("A ordem precisa ter um orçamento antes do faturamento.")
    try:
        total = TotaisOrcamento.objects.get(pk=orcamento.pk).total_final
    except TotaisOrcamento.DoesNotExist:
        raise ValidationError("A ordem precisa ter um orçamento antes do faturamento.")
    if quantidade_parcelas < 1 or quantidade_parcelas > 24:
        raise ValidationError("Use de 1 a 24 parcelas.")
    faturamento = Faturamento.objects.create(ordem=ordem, valor_total=total, emitido_em=timezone.localdate(), observacao=observacao, criado_por=ator)
    valor_base = (total / quantidade_parcelas).quantize(CENTAVO, rounding=ROUND_HALF_UP)
    soma = Decimal("0.00")
    for indice in range(quantidade_parcelas):
        valor = total - soma if indice == quantidade_parcelas - 1 else valor_base
        soma += valor
        ParcelaReceber.objects.create(faturamento=faturamento, numero=indice + 1, valor=valor, vencimento=_somar_mes(primeiro_vencimento, indice))
    return faturamento


@transaction.atomic
def gerar_comissao(*, ordem, profissional, percentual, ator):
    orçamento = ordem.orcamentos.order_by("-revisao").first()
    if not orçamento:
        raise ValidationError("A ordem precisa de um orçamento para calcular comissão.")
    total = TotaisOrcamento.objects.get(orcamento_id=orçamento.pk).total_final
    percentual = Decimal(str(percentual))
    if percentual < 0 or percentual > 100:
        raise ValidationError("O percentual deve estar entre 0 e 100.")
    valor = (total * percentual / Decimal("100")).quantize(CENTAVO, rounding=ROUND_HALF_UP)
    return Comissao.objects.create(ordem=ordem, profissional=profissional, percentual=percentual, base_calculo=total, valor=valor, criado_por=ator)
