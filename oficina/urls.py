from django.urls import path

from oficina import views

urlpatterns = [
    path("", views.painel, name="painel"),
    path("clientes/", views.clientes, name="clientes"),
    path("clientes/novo/", views.cliente_novo, name="cliente_novo"),
    path("veiculos/", views.veiculos, name="veiculos"),
    path("veiculos/novo/", views.veiculo_novo, name="veiculo_novo"),
    path("ordens/", views.ordens, name="ordens"),
    path("ordens/nova/", views.ordem_nova, name="ordem_nova"),
    path("ordens/<int:pk>/", views.ordem_detalhe, name="ordem_detalhe"),
    path("ordens/<int:ordem_id>/orcamento/", views.orcamento_editar, name="orcamento_editar"),
    path("orcamentos/<int:pk>/pdf/", views.orcamento_pdf, name="orcamento_pdf"),
    path("estoque/", views.estoque, name="estoque"),
    path("financeiro/", views.financeiro, name="financeiro"),
    path("financeiro/criar/", views.financeiro_criar, name="financeiro_criar"),
    path("financeiro/baixar/<str:tipo>/<int:pk>/", views.financeiro_pagar, name="financeiro_pagar"),
]
