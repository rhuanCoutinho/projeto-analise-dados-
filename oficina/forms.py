from django import forms
from django.forms import formset_factory

from oficina.models import (
    Cliente, Comissao, ContaPagar, FotoVistoria, Faturamento, ItemOrcamento,
    MovimentoEstoque, OrdemServico, Orcamento, ProdutoEstoque, Seguradora,
    StatusOrdemServico, Veiculo,
)


class ClienteForm(forms.ModelForm):
    class Meta:
        model = Cliente
        fields = ["nome", "telefone", "email", "consentimento_dados", "observacao"]
        widgets = {"observacao": forms.Textarea(attrs={"rows": 2})}


class VeiculoForm(forms.ModelForm):
    class Meta:
        model = Veiculo
        fields = ["cliente", "placa", "marca", "modelo", "ano", "seguradora"]

    def clean_placa(self):
        return self.cleaned_data["placa"].upper().replace("-", "").replace(" ", "")


class OrdemServicoForm(forms.ModelForm):
    class Meta:
        model = OrdemServico
        fields = ["cliente", "veiculo", "descricao", "funileiro_responsavel", "pintor_responsavel"]
        widgets = {"descricao": forms.Textarea(attrs={"rows": 3})}

    def clean(self):
        dados = super().clean()
        cliente, veiculo = dados.get("cliente"), dados.get("veiculo")
        if cliente and veiculo and veiculo.cliente_id != cliente.id:
            self.add_error("veiculo", "Selecione um veículo pertencente a este cliente.")
        return dados


class FotoVistoriaForm(forms.ModelForm):
    class Meta:
        model = FotoVistoria
        fields = ["tipo", "arquivo", "descricao"]


class OrcamentoCabecalhoForm(forms.ModelForm):
    class Meta:
        model = Orcamento
        fields = ["desconto_percentual", "validade"]
        widgets = {"validade": forms.DateInput(attrs={"type": "date"})}


class ItemOrcamentoForm(forms.ModelForm):
    class Meta:
        model = ItemOrcamento
        fields = ["tipo", "descricao", "quantidade", "custo_unitario", "preco_unitario"]


ItemOrcamentoFormSet = formset_factory(ItemOrcamentoForm, extra=3, can_delete=True)


class StatusOSForm(forms.Form):
    status = forms.ChoiceField(choices=StatusOrdemServico.choices)
    observacao = forms.CharField(max_length=300, required=False)


class MovimentoEstoqueForm(forms.ModelForm):
    class Meta:
        model = MovimentoEstoque
        fields = ["produto", "tipo", "quantidade", "custo_unitario", "ordem", "motivo"]


class ProdutoEstoqueForm(forms.ModelForm):
    class Meta:
        model = ProdutoEstoque
        fields = ["codigo", "nome", "tipo", "unidade", "estoque_minimo", "custo_unitario", "ativo"]


class FaturamentoForm(forms.ModelForm):
    quantidade_parcelas = forms.IntegerField(min_value=1, max_value=24, initial=1, label="Número de parcelas")
    primeiro_vencimento = forms.DateField(widget=forms.DateInput(attrs={"type": "date"}), label="Primeiro vencimento")

    class Meta:
        model = Faturamento
        fields = ["ordem", "emitido_em", "observacao"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["ordem"].queryset = OrdemServico.objects.filter(status=StatusOrdemServico.ENTREGUE)


class ContaPagarForm(forms.ModelForm):
    class Meta:
        model = ContaPagar
        fields = ["descricao", "fornecedor", "valor", "vencimento"]
        widgets = {"vencimento": forms.DateInput(attrs={"type": "date"})}


class ComissaoForm(forms.ModelForm):
    class Meta:
        model = Comissao
        fields = ["ordem", "profissional", "percentual"]


class SeguradoraForm(forms.ModelForm):
    class Meta:
        model = Seguradora
        fields = ["nome", "telefone", "email", "ativa"]
