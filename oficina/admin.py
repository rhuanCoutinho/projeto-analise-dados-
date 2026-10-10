from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin
from django.contrib.auth.models import User

from oficina.models import (
    Auditoria, Cliente, Comissao, ContaPagar, FotoVistoria, Faturamento,
    HistoricoStatusOS, ItemOrcamento, MovimentoEstoque, OrdemServico,
    Orcamento, ParcelaReceber, PerfilUsuario, ProdutoEstoque, Seguradora,
    Veiculo,
)


class PerfilInline(admin.StackedInline):
    model = PerfilUsuario
    can_delete = False
    extra = 1


class UsuarioAdmin(DjangoUserAdmin):
    inlines = [PerfilInline]


admin.site.unregister(User)
admin.site.register(User, UsuarioAdmin)


class ItemInline(admin.TabularInline):
    model = ItemOrcamento
    extra = 0


@admin.register(Orcamento)
class OrcamentoAdmin(admin.ModelAdmin):
    list_display = ("ordem", "revisao", "status", "desconto_percentual", "atualizado_em")
    list_filter = ("status",)
    inlines = [ItemInline]
    readonly_fields = ("criado_em", "atualizado_em")
    def has_add_permission(self, request):
        return False
    def has_change_permission(self, request, obj=None):
        return False


@admin.register(OrdemServico)
class OrdemServicoAdmin(admin.ModelAdmin):
    list_display = ("codigo", "cliente", "veiculo", "status", "data_abertura")
    list_filter = ("status", "data_abertura")
    search_fields = ("codigo", "cliente__nome", "veiculo__placa", "veiculo__modelo")
    readonly_fields = ("codigo", "data_abertura", "atualizado_em")
    # Status só pode ser alterado pelo fluxo de transição, que escreve o histórico.
    exclude = ("status",)
    def has_add_permission(self, request):
        return False
    def has_change_permission(self, request, obj=None):
        return False


@admin.register(HistoricoStatusOS)
class HistoricoStatusAdmin(admin.ModelAdmin):
    list_display = ("ordem", "status_anterior", "status_novo", "alterado_por", "criado_em")
    readonly_fields = ("ordem", "status_anterior", "status_novo", "alterado_por", "observacao", "criado_em")
    def has_add_permission(self, request):
        return False
    def has_change_permission(self, request, obj=None):
        return False
    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Auditoria)
class AuditoriaAdmin(admin.ModelAdmin):
    list_display = ("criado_em", "ator", "acao", "content_type", "objeto_id")
    list_filter = ("acao", "content_type", "criado_em")
    readonly_fields = ("ator", "acao", "content_type", "objeto_id", "antes", "depois", "criado_em")
    def has_add_permission(self, request):
        return False
    def has_change_permission(self, request, obj=None):
        return False
    def has_delete_permission(self, request, obj=None):
        return False


admin.site.register([Cliente, Veiculo, Seguradora, FotoVistoria, ProdutoEstoque, MovimentoEstoque, Faturamento, ParcelaReceber, ContaPagar, Comissao])
