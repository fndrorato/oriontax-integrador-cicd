import re
from decimal import Decimal, InvalidOperation
from django import forms
from cattles.models import MatrixSimulation, FieldConfiguration, FieldOption


def parse_decimal_br(value_str):
    """
    Converte string brasileira (ex: "R$ 87.482,00" ou "50,00 %") em Decimal.
    Retorna None se a string for vazia ou não puder ser convertida.
    """
    if not value_str:
        return None
    # Remove R$, %, espaços e pontos de milhar, substitui vírgula por ponto decimal
    clean = re.sub(r'[R$%\s.]', '', value_str).replace(',', '.')
    try:
        return Decimal(clean)
    except InvalidOperation: # Captura erro se a string final não for um decimal válido
        return None
    except Exception as e:
        print(f"Erro inesperado ao parsear '{value_str}': {e}")
        return None

class MatrixSimulationForm(forms.ModelForm):
    
    def clean(self):
        cleaned_data = super().clean()
        decimal_fields = [
            'monthly_sales_volume_kg', 'total_sales_per_month', 'average_price_per_kg',
            'cows_per_month_producer', 'cows_per_month_slaughterhouse',
            'cows_per_week_producer', 'cows_per_week_slaughterhouse',
            'mean_weight_per_cow_producer_kg', 'mean_weight_per_cow_slaughterhouse_kg',
            'mean_weight_per_cow_producer_arroba',
            'yield_live_cow_pasture_producer_percent', 'yield_butchered_cow_producer_percent',
            'yield_butchered_cow_slaughterhouse_percent',
            'price_closed_per_arroba_producer', 'price_per_kg_butchered_cow_slaughterhouse',
            'price_net_per_arroba_producer', 'price_per_kg_butchered_cow_producer',
            'price_per_kg_after_butchered_cow_producer', 'price_per_kg_after_butchered_cow_slaughterhouse',
            'slaughter_service_per_cow_producer', 'freight_producer_slaughterhouse_producer',
            'freight_slaughterhouse_store_producer', 'freight_slaughterhouse_store_slaughterhouse',
            'commission_buyer', 'total_slaughter_cost', 'total_value_producer',
            'total_value_slaughterhouse', 'profit_gain_comparison',
        ]
        for field in decimal_fields:
            val = self.data.get(field)
            cleaned_data[field] = parse_decimal_br(val)

        return cleaned_data
        
    granted_credit_percent = forms.DecimalField(
        max_digits=5,
        decimal_places=2,
        required=False,
        label="Crédito Outorgado (%)",
        widget=forms.TextInput(attrs={
            'class': 'form-control autonumeric',
            'inputmode': 'decimal',
            'readonly': True,
        })
    )
    icms_debit_producer = forms.DecimalField(
        max_digits=5, decimal_places=2, required=False, label="ICMS Débito Produtor",
        widget=forms.TextInput(attrs={
            'class': 'form-control autonumeric',
            'readonly': True,
            'inputmode': 'decimal'
        })
    )
    icms_debit_slaughterhouse = forms.DecimalField(
        max_digits=5, decimal_places=2, required=False, label="ICMS Débito Frigorífico",
        widget=forms.TextInput(attrs={'class': 'form-control autonumeric', 'readonly': True})
    )
    icms_credit_slaughterhouse = forms.DecimalField(
        max_digits=5, decimal_places=2, required=False, label="ICMS Crédito Frigorífico",
        widget=forms.TextInput(attrs={'class': 'form-control autonumeric', 'readonly': True})
    )
    icms_loss_reversal_percent = forms.DecimalField(
        max_digits=5, decimal_places=2, required=False, label="Estorno ICMS da Perda (%)",
        widget=forms.TextInput(attrs={'class': 'form-control autonumeric', 'readonly': True})
    )
    protege_percent = forms.DecimalField(
        max_digits=5, decimal_places=2, required=False, label="PROTEGE (%)",
        widget=forms.TextInput(attrs={'class': 'form-control autonumeric', 'readonly': True})
    )
    fundeinfra_percent = forms.DecimalField(
        max_digits=5, decimal_places=2, required=False, label="FUNDEINFRO (%)",
        widget=forms.TextInput(attrs={'class': 'form-control autonumeric', 'readonly': True})
    )
    tax_producer_real = forms.DecimalField(
        max_digits=5, decimal_places=2, required=False, label="Imposto Efetivo Produtor (R$)",
        widget=forms.TextInput(attrs={'class': 'form-control autonumeric', 'readonly': True})
    )
    tax_slaughterhouse_real = forms.DecimalField(
        max_digits=5, decimal_places=2, required=False, label="Imposto Efetivo Frigorífico",
        widget=forms.TextInput(attrs={'class': 'form-control autonumeric', 'readonly': True})
    )
    tax_producer_percent = forms.DecimalField(
        max_digits=5, decimal_places=2, required=False, label="Imposto Efetivo Produtor (%)",
        widget=forms.TextInput(attrs={'class': 'form-control autonumeric', 'readonly': True})
    )              
    tax_slaughterhouse_percent = forms.DecimalField(
        max_digits=5, decimal_places=2, required=False, label="Imposto Efetivo Frigorífico (%)",
        widget=forms.TextInput(attrs={'class': 'form-control autonumeric', 'readonly': True})
    )   
    profit_producer_real = forms.DecimalField(
        max_digits=5, decimal_places=2, required=False, label="Margem de Lucro Produtor (R$)",
        widget=forms.TextInput(attrs={'class': 'form-control autonumeric', 'readonly': True})
    )
    profit_slaughterhouse_real = forms.DecimalField(
        max_digits=5, decimal_places=2, required=False, label="Margem de Lucro Frigorífico (R$)",
        widget=forms.TextInput(attrs={'class': 'form-control autonumeric', 'readonly': True})
    )
    profit_producer_percent = forms.DecimalField(
        max_digits=5, decimal_places=2, required=False, label="Margem de Lucro Produtor (%)",
        widget=forms.TextInput(attrs={'class': 'form-control autonumeric', 'readonly': True})
    )
    profit_slaughterhouse_percent = forms.DecimalField(
        max_digits=5, decimal_places=2, required=False, label="Margem de Lucro Frigorífico (%)",
        widget=forms.TextInput(attrs={'class': 'form-control autonumeric', 'readonly': True})
    )
    economia_mensal = forms.DecimalField(
        max_digits=5, decimal_places=2, required=False, label="Economia Mensal (R$)",
        widget=forms.TextInput(attrs={'class': 'form-control autonumeric economia-input', 'readonly': True})
    )
    economia_anual = forms.DecimalField(
        max_digits=5, decimal_places=2, required=False, label="Economia Anual (R$)",
        widget=forms.TextInput(attrs={'class': 'form-control autonumeric economia-input', 'readonly': True})
    )
    economia_arroba = forms.DecimalField(
        max_digits=5, decimal_places=2, required=False, label="Economia Arroba",
        widget=forms.TextInput(attrs={'class': 'form-control autonumeric economia-input', 'readonly': True})
    )
    economia_kg = forms.DecimalField(
        max_digits=5, decimal_places=2, required=False, label="Economia Kg",
        widget=forms.TextInput(attrs={'class': 'form-control autonumeric economia-input', 'readonly': True})
    )    
    icms_debit_value = forms.DecimalField(
        required=False,
        widget=forms.HiddenInput()
    )
    icms_credit_value = forms.DecimalField(
        required=False,
        widget=forms.HiddenInput()
    )   
    granted_credit_value = forms.DecimalField(
        required=False,
        widget=forms.HiddenInput()
    )
    icms_loss_reversal_value = forms.DecimalField(
        required=False,
        widget=forms.HiddenInput()
    )   
    protege_value = forms.DecimalField(
        required=False,
        widget=forms.HiddenInput()
    )
    fundeinfra_value = forms.DecimalField(
        required=False,
        widget=forms.HiddenInput()
    )             
    

    class Meta:
        model = MatrixSimulation
        exclude = ['user', 'created_at', 'updated_at']
        widgets = {
            'monthly_sales_volume_kg': forms.TextInput(attrs={'class': 'form-control autonumeric', 'inputmode': 'decimal'}),
            'total_sales_per_month': forms.TextInput(attrs={'class': 'form-control autonumeric', 'readonly': True}),
            'average_price_per_kg': forms.TextInput(attrs={'class': 'form-control autonumeric', 'inputmode': 'decimal'}),
            'cows_per_month_producer': forms.TextInput(attrs={'class': 'form-control autonumeric', 'readonly': True}),
            'cows_per_month_slaughterhouse': forms.TextInput(attrs={'class': 'form-control autonumeric', 'readonly': True}),
            'cows_per_week_producer': forms.TextInput(attrs={'class': 'form-control autonumeric', 'readonly': True}),
            'cows_per_week_slaughterhouse': forms.TextInput(attrs={'class': 'form-control autonumeric', 'readonly': True}),
            'mean_weight_per_cow_producer_arroba': forms.TextInput(attrs={
                'class': 'form-control autonumeric',
                'readonly': True
            }),
            'mean_weight_per_cow_slaughterhouse_kg': forms.TextInput(attrs={
                'class': 'form-control autonumeric',
            }),
            'yield_live_cow_pasture_producer_percent': forms.TextInput(attrs={'class': 'form-control autonumeric'}),
            'yield_butchered_cow_producer_percent': forms.TextInput(attrs={'class': 'form-control autonumeric'}),
            'yield_live_cow_pasture_slaughterhouse_percent': forms.TextInput(attrs={'class': 'form-control autonumeric'}),
            'yield_butchered_cow_slaughterhouse_percent': forms.TextInput(attrs={'class': 'form-control autonumeric', 'readonly': True}),   
            'price_closed_per_arroba_producer': forms.TextInput(attrs={'class': 'form-control autonumeric'}),
            'price_closed_per_arroba_slaughterhouse': forms.TextInput(attrs={'class': 'form-control autonumeric'}),
            'price_net_per_arroba_producer': forms.TextInput(attrs={'class': 'form-control autonumeric'}),
            'price_net_per_arroba_slaughterhouse': forms.TextInput(attrs={'class': 'form-control autonumeric'}),            
            'price_per_kg_butchered_cow_producer': forms.TextInput(attrs={'class': 'form-control autonumeric'}),
            'price_per_kg_butchered_cow_slaughterhouse': forms.TextInput(attrs={'class': 'form-control autonumeric'}),
            'price_per_kg_after_butchered_cow_producer': forms.TextInput(attrs={'class': 'form-control autonumeric'}),
            'price_per_kg_after_butchered_cow_slaughterhouse': forms.TextInput(attrs={'class': 'form-control autonumeric'}),
            'slaughter_service_per_cow_producer': forms.TextInput(attrs={'class': 'form-control autonumeric'}),
            'slaughter_service_per_cow_slaughterhouse': forms.TextInput(attrs={'class': 'form-control autonumeric'}),
            'freight_producer_slaughterhouse_producer': forms.TextInput(attrs={'class': 'form-control autonumeric'}),
            'freight_slaughterhouse_store_producer': forms.TextInput(attrs={'class': 'form-control autonumeric'}),            
            'freight_slaughterhouse_store_slaughterhouse': forms.TextInput(attrs={'class': 'form-control autonumeric'}),            
            'commission_buyer': forms.TextInput(attrs={'class': 'form-control autonumeric economia-input', 'readonly': True}),
            'total_slaughter_cost': forms.TextInput(attrs={'class': 'form-control autonumeric economia-input', 'readonly': True}),
            'total_value_producer': forms.TextInput(attrs={'class': 'form-control autonumeric economia-input', 'readonly': True}),
            'total_value_slaughterhouse': forms.TextInput(attrs={'class': 'form-control autonumeric economia-input', 'readonly': True}),
            'profit_gain_comparison': forms.TextInput(attrs={'class': 'form-control autonumeric economia-input', 'readonly': True}),        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Substitui completamente o campo para manter funcionalidade e estilo
        try:
            config_icms_debit = FieldConfiguration.objects.get(field_name='icms_debit_percent')
            icms_debit = FieldOption.objects.filter(field=config_icms_debit).first()
            if icms_debit:
                self.fields['icms_debit_value'].initial = icms_debit.value

            config_icms_credit = FieldConfiguration.objects.get(field_name='icms_credit_percent')
            icms_credit = FieldOption.objects.filter(field=config_icms_credit).first()
            if icms_credit:
                self.fields['icms_credit_value'].initial = icms_credit.value

            config_granted_credit = FieldConfiguration.objects.get(field_name='granted_credit_percent')
            granted_credit = FieldOption.objects.filter(field=config_granted_credit).first()
            if granted_credit:
                self.fields['granted_credit_value'].initial = granted_credit.value

            config_icms_loss_reversal = FieldConfiguration.objects.get(field_name='icms_loss_reversal_percent')
            icms_loss_reversal = FieldOption.objects.filter(field=config_icms_loss_reversal).first()
            if icms_loss_reversal:
                self.fields['icms_loss_reversal_value'].initial = icms_loss_reversal.value

            config_protege = FieldConfiguration.objects.get(field_name='protege_percent')
            protege = FieldOption.objects.filter(field=config_protege).first()
            if protege:
                self.fields['protege_value'].initial = protege.value
                
            config_fundeinfra = FieldConfiguration.objects.get(field_name='fundeinfra_percent')
            fundeinfra = FieldOption.objects.filter(field=config_fundeinfra).first()
            if fundeinfra:
                self.fields['fundeinfra_value'].initial = fundeinfra.value                

            config = FieldConfiguration.objects.get(field_name='cow_weighing_location')
            options = FieldOption.objects.filter(field=config)

            self.fields['cow_weighing_location'] = forms.ChoiceField(
                label="Onde será pesada a vaca?",
                choices=[(opt.value, opt.label) for opt in options],
                widget=forms.Select(attrs={'class': 'form-control select2 custom-select-bg'})
            )
        except FieldConfiguration.DoesNotExist:
            self.fields['cow_weighing_location'] = forms.ChoiceField(
                label="Onde será pesada a vaca?",
                choices=[],
                widget=forms.Select(attrs={'class': 'form-control select2 custom-select-bg'})
            )