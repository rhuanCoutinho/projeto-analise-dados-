"""Registro explícito de alterações sensíveis com usuário, valores antes e depois."""
from django.contrib.contenttypes.models import ContentType

from oficina.models import Auditoria


def registrar_auditoria(*, ator, objeto, acao, antes=None, depois=None):
    return Auditoria.objects.create(
        ator=ator,
        acao=acao,
        content_type=ContentType.objects.get_for_model(objeto),
        objeto_id=str(objeto.pk),
        antes=antes or {},
        depois=depois or {},
    )
