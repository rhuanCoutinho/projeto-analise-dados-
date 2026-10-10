"""Tabela pura de estados para testar o fluxo sem depender de infraestrutura."""

TRANSICOES_VALIDAS = {
    "vistoria": {"orcamento", "cancelada"},
    "orcamento": {"aguardando_aprovacao", "aprovado", "cancelada"},
    "aguardando_aprovacao": {"orcamento", "aprovado", "cancelada"},
    "aprovado": {"aguardando_pecas", "funilaria", "cancelada"},
    "aguardando_pecas": {"funilaria", "cancelada"},
    "funilaria": {"preparacao", "pintura", "cancelada"},
    "preparacao": {"pintura", "cancelada"},
    "pintura": {"polimento", "cancelada"},
    "polimento": {"pronta", "cancelada"},
    "pronta": {"entregue", "cancelada"},
    "entregue": set(),
    "cancelada": set(),
}


def validar_transicao(status_atual, status_novo):
    if status_novo not in TRANSICOES_VALIDAS.get(status_atual, set()):
        raise ValueError(f"Transição inválida: {status_atual} -> {status_novo}.")
