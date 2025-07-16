import re
from base.models import States
from decimal import Decimal, InvalidOperation
from django import forms
from pricing.models import Pricing 
from shopsim.models import SupplierProfile


class BrazilianDecimalField(forms.DecimalField):
    def to_python(self, value):
        if value in self.empty_values:
            return None if not self.required else value

        if isinstance(value, Decimal):
            return value

        if not isinstance(value, str):
            value = str(value)

        # Remove 'R$', '%', espaços e pontos de milhar, depois substitui vírgula por ponto
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
            # Captura exceções genéricas para diagnóstico, mas InvalidOperation é o principal
            raise forms.ValidationError(
                f"Erro inesperado ao processar o número: {e}",
                code='unexpected_error',
            )

    default_error_messages = {
        'invalid': 'Informe um número válido no formato brasileiro (ex: 1.234,56).',
    }

# Define as opções para os campos booleanos Sim/Não
BOOLEAN_CHOICES = (
    ('False', 'Não'),
    ('True', 'Sim'),
)

class PricingForm(forms.ModelForm):
    # Campos que se tornarão selects no template
    state_option = forms.ModelChoiceField(
        queryset=States.objects.all(),
        label="Estado:",
        empty_label="Selecione um estado",
        widget=forms.Select(attrs={'class': 'form-control'}) 
    )
    
    # item_icms_excluded = forms.ChoiceField(
    #     choices=BOOLEAN_CHOICES,
    #     label="Produto está nas exceções do ICMS?",
    #     widget=forms.Select(attrs={'class': 'form-control'})
    # )
    
    tax_icms_sale = BrazilianDecimalField(
        max_digits=5, # Ajuste conforme a precisão necessária para o markup
        decimal_places=2,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )    
    
    items_pis_cofins_excluded = forms.ChoiceField(
        choices=BOOLEAN_CHOICES,
        label="Produto está nas exceções do PIS/COFINS?",
        widget=forms.Select(attrs={'class': 'form-control'})
    )

    supplier = forms.ModelChoiceField(
        queryset=SupplierProfile.objects.all(),
        label="Fornecedor:",
        empty_label="Selecione o Fornecedor",
        widget=forms.Select(attrs={'class': 'form-control'})
    )

    markup = BrazilianDecimalField(
        max_digits=5, # Ajuste conforme a precisão necessária para o markup
        decimal_places=2,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    
    sale_price = BrazilianDecimalField( # Este é o campo que será salvo no MODELO Pricing
        max_digits=10, decimal_places=2, required=True, # Ajuste required conforme seu modelo
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )    
    
    card_tax = BrazilianDecimalField(
        max_digits=5, # Ajuste conforme a precisão necessária para a taxa
        decimal_places=2,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    
    operational_cost_percentage_display = BrazilianDecimalField(
        required=False, 
        max_digits=5, decimal_places=2,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )    
    
    cost_price = BrazilianDecimalField( # Este é o campo que recebe "R$ 17,00" do input do usuário
        max_digits=10, # Ajuste conforme o máximo esperado para preços
        decimal_places=2,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )

    sale_price_display = BrazilianDecimalField( # Se você realmente quer validar este valor que vem do JS
        max_digits=10, decimal_places=2, required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'readonly': 'readonly'})
    )
    
    # Campos para Créditos e Débitos (display only - não incluídos no Meta.fields)
    pis_credit_display = forms.CharField(required=False, widget=forms.TextInput(attrs={'class': 'form-control', 'readonly': 'readonly'}))
    cofins_credit_display = forms.CharField(required=False, widget=forms.TextInput(attrs={'class': 'form-control', 'readonly': 'readonly'}))
    icms_credit_display = forms.CharField(required=False, widget=forms.TextInput(attrs={'class': 'form-control', 'readonly': 'readonly'}))
    pis_debit_display = forms.CharField(required=False, widget=forms.TextInput(attrs={'class': 'form-control', 'readonly': 'readonly'}))
    cofins_debit_display = forms.CharField(required=False, widget=forms.TextInput(attrs={'class': 'form-control', 'readonly': 'readonly'}))
    icms_debit_display = forms.CharField(required=False, widget=forms.TextInput(attrs={'class': 'form-control', 'readonly': 'readonly'}))

    # Campos de Resultado (display only - não incluídos no Meta.fields)
    liquid_margin_value_display = forms.CharField(required=False, widget=forms.TextInput(attrs={'class': 'form-control', 'readonly': 'readonly'}))
    gross_margin_percentage_display = forms.CharField(required=False, widget=forms.TextInput(attrs={'class': 'form-control', 'readonly': 'readonly'}))
    
    mark_down_percentage_display = forms.CharField(required=False, widget=forms.TextInput(attrs={'class': 'form-control', 'readonly': 'readonly'}))
    liquid_margin_final_percentage_display = forms.CharField(required=False, widget=forms.TextInput(attrs={'class': 'form-control', 'readonly': 'readonly'}))

    # Campo para a descrição da simulação (do seu QueryDict)
    item_description = forms.CharField(
        label="Produto:",
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Descrição do Produto'}),
        required=True # Assumindo que a descrição é obrigatória
    )    
    
    description = forms.CharField(
        label="Descrição:",
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Descrição da Precificação'}),
        required=True # Assumindo que a descrição é obrigatória
    )

    total_cost_at_moment = BrazilianDecimalField( # Supondo que ele também venha formatado
        max_digits=10, decimal_places=2, required=False,
        widget=forms.HiddenInput()
    )
    


    class Meta:
        model = Pricing

        fields = [
            'description',
            'item_description',
            'tax_icms_sale',
            'items_pis_cofins_excluded',
            'state_option',
            'supplier',
            'markup',
            'card_tax',
            'cost_price', # Este é o custo base que o usuário informa
            'total_cost_at_moment', # Se você quiser salvar o total_cost_at_moment que vem do JS
            'sale_price', # Se você quer salvar o sale_price calculado pelo JS
            'operational_cost_percentage_display',
        ]
     
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Ajuste a label para 'description' para coincidir com o HTML
        self.fields['description'].label = "Descrição da Simulação:"
        
    def clean(self):
        # Apenas chame o clean do pai. BrazilianDecimalField já fez seu trabalho.
        cleaned_data = super().clean()
        # Adicione aqui qualquer lógica de validação cruzada, se necessário.
        return cleaned_data        

    def clean_items_pis_cofins_excluded(self):
        # Converte a string 'True'/'False' para booleano
        value = self.cleaned_data['items_pis_cofins_excluded']
        return value == 'True'
