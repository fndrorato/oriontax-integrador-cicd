from base.models import States
from django import forms
from shopsim.models import PriceQuote, SupplierProfile
from decimal import Decimal, InvalidOperation
import re 

# --- COLOQUE A CLASSE BrazilianDecimalField AQUI OU IMPORTE-A ---
# (Assumindo que você a colocou no mesmo arquivo por enquanto)
class BrazilianDecimalField(forms.DecimalField):
    def to_python(self, value):
        if value in self.empty_values:
            return None if not self.required else value

        if isinstance(value, Decimal):
            return value

        if not isinstance(value, str):
            value = str(value)

        clean_value = re.sub(r'[R$%\s.]', '', value, flags=re.IGNORECASE).replace(',', '.')

        if not clean_value and not self.required:
            return None

        try:
            return Decimal(clean_value)
        except InvalidOperation:
            raise forms.ValidationError(
                self.error_messages['invalid'],
                code='invalid',
            )
        except Exception as e:
            raise forms.ValidationError(
                f"Erro inesperado ao processar o número: {e}",
                code='unexpected_error',
            )

    default_error_messages = {
        'invalid': 'Informe um número válido no formato brasileiro (ex: 1.234,56).',
    }
# --- FIM DA CLASSE BrazilianDecimalField ---


class PriceQuoteForm(forms.ModelForm):
    BOOLEAN_CHOICES = [
        (False, 'Não'),
        (True, 'Sim'),
    ]

    product_icms_7 = forms.TypedChoiceField(
        choices=BOOLEAN_CHOICES,
        coerce=lambda x: x == 'True',
        widget=forms.Select(attrs={'class': 'form-control'}),
        label="Produto é 7% no ICMS?"
    )
    product_pis_cofins = forms.TypedChoiceField(
        choices=BOOLEAN_CHOICES,
        coerce=lambda x: x == 'True',
        widget=forms.Select(attrs={'class': 'form-control'}),
        label="Produto é tributado PIS/COFINS?"
    )

    state_option_01 = forms.ModelChoiceField(
        queryset=States.objects.all(),
        widget=forms.Select(attrs={'class': 'form-control'}),
        label="Estado de compra (Opção 1)"
    )
    state_option_02 = forms.ModelChoiceField(
        queryset=States.objects.all(),
        widget=forms.Select(attrs={'class': 'form-control'}),
        label="Estado de compra (Opção 2)"
    )
    supplier_profile_01 = forms.ModelChoiceField(
        queryset=SupplierProfile.objects.all(),
        widget=forms.Select(attrs={'class': 'form-control'}),
        label="Perfil do Fornecedor (Opção 1)"
    )
    supplier_profile_02 = forms.ModelChoiceField(
        queryset=SupplierProfile.objects.all(),
        widget=forms.Select(attrs={'class': 'form-control'}),
        label="Perfil do Fornecedor (Opção 2)"
    )

    # --- CAMPOS NUMÉRICOS AGORA USAM BrazilianDecimalField ---
    product_price_01 = BrazilianDecimalField(
        max_digits=10, decimal_places=2, required=False,
        widget=forms.TextInput(attrs={'class': 'form-control autonumeric'})
    )
    product_price_02 = BrazilianDecimalField(
        max_digits=10, decimal_places=2, required=False,
        widget=forms.TextInput(attrs={'class': 'form-control autonumeric'})
    )
    freight_01 = BrazilianDecimalField(
        max_digits=10, decimal_places=2, required=False,
        widget=forms.TextInput(attrs={'class': 'form-control autonumeric'})
    )
    freight_02 = BrazilianDecimalField(
        max_digits=10, decimal_places=2, required=False,
        widget=forms.TextInput(attrs={'class': 'form-control autonumeric'})
    )
    additional_costs_01 = BrazilianDecimalField(
        max_digits=10, decimal_places=2, required=False,
        widget=forms.TextInput(attrs={'class': 'form-control autonumeric'})
    )
    additional_costs_02 = BrazilianDecimalField(
        max_digits=10, decimal_places=2, required=False,
        widget=forms.TextInput(attrs={'class': 'form-control autonumeric'})
    )
    # --- FIM DOS CAMPOS NUMÉRICOS ---

    # Campos de exibição (display fields) - Mantemos como CharField e readonly
    aliquota_inter_display_01 = forms.CharField(max_length=10, required=False, widget=forms.TextInput(attrs={'class': 'form-control', 'readonly': 'readonly'}))
    aliquota_inter_display_02 = forms.CharField(max_length=10, required=False, widget=forms.TextInput(attrs={'class': 'form-control', 'readonly': 'readonly'}))
    icms_credit_display_01 = forms.CharField(max_length=15, required=False, widget=forms.TextInput(attrs={'class': 'form-control', 'readonly': 'readonly'}))
    icms_credit_display_02 = forms.CharField(max_length=15, required=False, widget=forms.TextInput(attrs={'class': 'form-control', 'readonly': 'readonly'}))
    pis_cofins_credit_display_01 = forms.CharField(max_length=15, required=False, widget=forms.TextInput(attrs={'class': 'form-control', 'readonly': 'readonly'}))
    pis_cofins_credit_display_02 = forms.CharField(max_length=15, required=False, widget=forms.TextInput(attrs={'class': 'form-control', 'readonly': 'readonly'}))
    total_cost_display_01 = forms.CharField(max_length=15, required=False, widget=forms.TextInput(attrs={'class': 'form-control', 'readonly': 'readonly'}))
    total_cost_display_02 = forms.CharField(max_length=15, required=False, widget=forms.TextInput(attrs={'class': 'form-control', 'readonly': 'readonly'}))

    # best_option permanece como CharField para receber o ID ou 'Empate'
    best_option = forms.CharField(max_length=50, required=False, widget=forms.HiddenInput(attrs={'class': 'form-control', 'readonly': 'readonly'}))

    class Meta:
        model = PriceQuote
        fields = [
            'simulation_description',
            'product_icms_7',
            'product_pis_cofins',
            'product_description',
            'state_option_01',
            'supplier_profile_01',
            'product_price_01', # Estes campos agora serão gerenciados por BrazilianDecimalField
            'freight_01',
            'additional_costs_01',
            'state_option_02',
            'supplier_profile_02',
            'product_price_02', # Estes campos agora serão gerenciados por BrazilianDecimalField
            'freight_02',
            'additional_costs_02',
        ]

        widgets = {
            'simulation_description': forms.TextInput(attrs={'class': 'form-control'}),
            'product_description': forms.TextInput(attrs={'class': 'form-control'}),
            # Remova os widgets específicos para product_price_01, etc.,
            # pois eles já estão definidos na declaração do BrazilianDecimalField acima.
            # Se você os deixar aqui, eles podem sobrescrever os widgets do BrazilianDecimalField.
            # Ex:
            # 'product_price_01': forms.TextInput(attrs={'class': 'form-control'}), # REMOVA ESTAS LINHAS
            # ...
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            # Ao editar, formate os valores do DecimalField do modelo para a exibição no TextInput
            # Isso é importante para que o autoNumeric possa inicializar corretamente
            # Use o método format_value do próprio campo para garantir consistência
            # ou faça a formatação manual como antes.
            # O .value_to_string é mais para ModelForms internos do Django, então a formatação manual é boa.
            self.fields['product_price_01'].initial = f"R$ {self.instance.product_price_01:.2f}".replace('.', ',') if self.instance.product_price_01 is not None else ''
            self.fields['product_price_02'].initial = f"R$ {self.instance.product_price_02:.2f}".replace('.', ',') if self.instance.product_price_02 is not None else ''
            self.fields['freight_01'].initial = f"R$ {self.instance.freight_01:.2f}".replace('.', ',') if self.instance.freight_01 is not None else ''
            self.fields['freight_02'].initial = f"R$ {self.instance.freight_02:.2f}".replace('.', ',') if self.instance.freight_02 is not None else ''
            self.fields['additional_costs_01'].initial = f"R$ {self.instance.additional_costs_01:.2f}".replace('.', ',') if self.instance.additional_costs_01 is not None else ''
            self.fields['additional_costs_02'].initial = f"R$ {self.instance.additional_costs_02:.2f}".replace('.', ',') if self.instance.additional_costs_02 is not None else ''

            self.fields['aliquota_inter_display_01'].initial = f"{self.instance.state_option_01.aliquota_inter:.2f}%".replace('.', ',') if self.instance.state_option_01 else ''
            self.fields['aliquota_inter_display_02'].initial = f"{self.instance.state_option_02.aliquota_inter:.2f}%".replace('.', ',') if self.instance.state_option_02 else ''

            self.fields['best_option'].initial = self.instance.best_option.id if self.instance.best_option else ''

    # Não precisamos mais dos métodos clean_product_price_01, etc.,
    # porque a lógica de limpeza já está no BrazilianDecimalField.
    # def clean_product_price_01(self): ...
    # def clean_freight_01(self): ...
    # ...

    def clean(self):
        # Apenas chame o clean do pai. BrazilianDecimalField já fez seu trabalho.
        cleaned_data = super().clean()
        # Adicione aqui qualquer lógica de validação cruzada, se necessário.
        return cleaned_data