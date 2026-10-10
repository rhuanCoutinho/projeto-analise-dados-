from decimal import Decimal

from django import template

register = template.Library()


@register.filter
def currency_brl(value):
    valor = Decimal(value or 0)
    texto = f"{valor:,.2f}"
    return "R$ " + texto.replace(",", "X").replace(".", ",").replace("X", ".")
