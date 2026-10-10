"""Regras de valor puras: não dependem de Django nem do banco."""
from decimal import Decimal, ROUND_HALF_UP

CENTAVO = Decimal("0.01")


def moeda(valor):
    return Decimal(str(valor)).quantize(CENTAVO, rounding=ROUND_HALF_UP)


def calcular_totais(itens, desconto_percentual=0):
    """Calcula peça, mão de obra, pintura, materiais, custo e desconto."""
    subtotal = sum((Decimal(str(i["quantidade"])) * Decimal(str(i["preco_unitario"])) for i in itens), Decimal("0"))
    custo_total = sum((Decimal(str(i.get("quantidade", 0))) * Decimal(str(i.get("custo_unitario", 0))) for i in itens), Decimal("0"))
    percentual = Decimal(str(desconto_percentual))
    if percentual < 0 or percentual > 100:
        raise ValueError("O desconto deve estar entre 0% e 100%.")
    desconto = moeda(subtotal * percentual / Decimal("100"))
    return {
        "subtotal": moeda(subtotal),
        "custo_total": moeda(custo_total),
        "desconto_percentual": percentual,
        "valor_desconto": desconto,
        "total_final": moeda(subtotal - desconto),
    }
