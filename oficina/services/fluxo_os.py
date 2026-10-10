"""Máquina de estados da OS: toda transição é validada e fica no histórico."""
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from oficina.models import HistoricoStatusOS, OrdemServico, Orcamento, StatusOrcamento, StatusOrdemServico
from oficina.domain.transicoes import TRANSICOES_VALIDAS as TRANSICOES_CODIGO, validar_transicao
from oficina.services.auditoria import registrar_auditoria

TRANSICOES_VALIDAS = {chave: {StatusOrdemServico(valor) for valor in valores} for chave, valores in TRANSICOES_CODIGO.items()}


@transaction.atomic
def transicionar_os(*, ordem_id, status_novo, ator, observacao=""):
    ordem = OrdemServico.objects.select_for_update().get(pk=ordem_id)
    if status_novo not in StatusOrdemServico.values:
        raise ValidationError("Status de OS inválido.")
    try:
        validar_transicao(ordem.status, status_novo)
    except ValueError:
        nome_novo = dict(StatusOrdemServico.choices).get(status_novo, status_novo)
        raise ValidationError(f"Não é permitido mover uma OS de '{ordem.get_status_display()}' para '{nome_novo}'.")
    if status_novo == StatusOrdemServico.APROVADO:
        orçamento_aprovado = Orcamento.objects.filter(ordem=ordem, status=StatusOrcamento.APROVADO).exists()
        if not orçamento_aprovado:
            raise ValidationError("A OS só pode ser aprovada depois da aprovação de um orçamento.")
    anterior = ordem.status
    ordem.status = status_novo
    if status_novo == StatusOrdemServico.ENTREGUE:
        ordem.data_entrega = timezone.now()
    ordem.save(update_fields=["status", "data_entrega", "atualizado_em"])
    HistoricoStatusOS.objects.create(ordem=ordem, status_anterior=anterior, status_novo=status_novo, alterado_por=ator, observacao=observacao)
    registrar_auditoria(ator=ator, objeto=ordem, acao="status_os_alterado", antes={"status": anterior}, depois={"status": status_novo, "observacao": observacao})
    return ordem


def registrar_abertura_os(ordem, ator):
    HistoricoStatusOS.objects.create(ordem=ordem, status_anterior="", status_novo=ordem.status, alterado_por=ator, observacao="Abertura da ordem de serviço")
