from functools import wraps

from django.contrib.auth.decorators import login_required
from django.core.exceptions import ObjectDoesNotExist, PermissionDenied

from oficina.models import PapelUsuario


def papel_do_usuario(usuario):
    if usuario.is_superuser:
        return PapelUsuario.DONO
    try:
        perfil = usuario.perfil_oficina
    except ObjectDoesNotExist:
        return None
    return perfil.papel if perfil.ativo else None


def papeis_permitidos(*papeis):
    def decorar(view):
        @login_required
        @wraps(view)
        def protegida(request, *args, **kwargs):
            if papel_do_usuario(request.user) not in papeis:
                raise PermissionDenied("Seu perfil não tem acesso a esta função.")
            return view(request, *args, **kwargs)
        return protegida
    return decorar


GESTAO = (PapelUsuario.DONO, PapelUsuario.ORCAMENTISTA)
OPERACAO = (PapelUsuario.DONO, PapelUsuario.ORCAMENTISTA, PapelUsuario.FUNILEIRO, PapelUsuario.PINTOR)
FINANCEIRO = (PapelUsuario.DONO, PapelUsuario.FINANCEIRO)
TODOS = tuple(PapelUsuario.values)
