from oficina.permissions import papel_do_usuario


ROTULOS_PAPEL = {
    "dono": "Dono",
    "orcamentista": "Orçamentista",
    "funileiro": "Funileiro",
    "pintor": "Pintor",
    "financeiro": "Financeiro",
}


def papel_usuario_contexto(request):
    papel = papel_do_usuario(request.user) if request.user.is_authenticated else None
    return {"papel": papel, "papel_label": ROTULOS_PAPEL.get(papel, "Equipe")}
