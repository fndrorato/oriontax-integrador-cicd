import re
from decimal import Decimal, InvalidOperation
from django import forms
from cattles.models import MatrixSimulation, FieldConfiguration, FieldOption

# 1. Crie um campo DecimalField personalizado para o formato brasileiro
class BrazilianDecimalField(forms.DecimalField):
    """
    Um campo DecimalField que aceita formato decimal brasileiro (vírgula como separador decimal,
    ponto como separador de milhares, e opcionalmente R$ ou %).
    """
    def to_python(self, value):
        """
        Converte a entrada do usuário (string) para um objeto Decimal.
        """
        if value in self.empty_values: # Lida com valores vazios (None, '', [])
            return None if self.required else None # Retorna None se não for obrigatório e permite nulo

        if isinstance(value, Decimal): # Se já for Decimal, retorna como está
            return value

        if not isinstance(value, str): # Se não for string nem Decimal, tenta converter para string
            value = str(value)

        # Remove 'R$', '%', espaços e pontos de milhar, depois substitui vírgula por ponto
        # Use a flag re.IGNORECASE para 'r$' também
        clean_value = re.sub(r'[R$%\s.]', '', value, flags=re.IGNORECASE).replace(',', '.')

        # Se após a limpeza a string estiver vazia, e o campo não for obrigatório, retorna None
        if not clean_value and not self.required:
            return None

        try:
            return Decimal(clean_value)
        except InvalidOperation:
            # Se a conversão falhar, levanta um ValidationError para o campo
            raise forms.ValidationError(
                self.error_messages['invalid'],
                code='invalid',
            )
        except Exception as e:
            # Para outros erros inesperados (improvável aqui, mas boa prática)
            raise forms.ValidationError(
                f"Erro inesperado ao processar o número: {e}",
                code='unexpected_error',
            )

    # Opcional: Adicionar mensagens de erro personalizadas
    default_error_messages = {
        'invalid': 'Informe um número válido no formato brasileiro (ex: 1.234,56).',
    }


class MatrixSimulationForm(forms.ModelForm):
    # 2. Declare explicitamente TODOS os campos DecimalField do seu MODELO
    # usando BrazilianDecimalField. Isso garante que sua lógica de limpeza
    # seja aplicada ANTES da validação padrão do Django.

    # Campos do modelo MatrixSimulation (ajustados para BrazilianDecimalField e max_digits)
    monthly_sales_volume_kg = BrazilianDecimalField(
        max_digits=12, decimal_places=2, required=True,
        widget=forms.TextInput(attrs={'class': 'form-control autonumeric', 'inputmode': 'decimal'})
    )
    average_price_per_kg = BrazilianDecimalField(
        max_digits=10, decimal_places=2, required=True,
        widget=forms.TextInput(attrs={'class': 'form-control autonumeric', 'inputmode': 'decimal'})
    )
    total_sales_per_month = BrazilianDecimalField(
        max_digits=12, decimal_places=2, required=False, # required=False se null=True no modelo
        widget=forms.TextInput(attrs={'class': 'form-control autonumeric', 'readonly': True})
    )
    cows_per_month_producer = BrazilianDecimalField(
        max_digits=12, decimal_places=2, required=False,
        widget=forms.TextInput(attrs={'class': 'form-control autonumeric', 'readonly': True})
    )
    cows_per_month_slaughterhouse = BrazilianDecimalField(
        max_digits=12, decimal_places=2, required=False,
        widget=forms.TextInput(attrs={'class': 'form-control autonumeric', 'readonly': True})
    )
    cows_per_week_producer = BrazilianDecimalField(
        max_digits=12, decimal_places=2, required=False,
        widget=forms.TextInput(attrs={'class': 'form-control autonumeric', 'readonly': True})
    )
    cows_per_week_slaughterhouse = BrazilianDecimalField(
        max_digits=12, decimal_places=2, required=False,
        widget=forms.TextInput(attrs={'class': 'form-control autonumeric', 'readonly': True})
    )
    mean_weight_per_cow_producer_arroba = BrazilianDecimalField(
        max_digits=10, decimal_places=2, required=False,
        widget=forms.TextInput(attrs={'class': 'form-control autonumeric', 'readonly': True})
    )
    mean_weight_per_cow_slaughterhouse_arroba = BrazilianDecimalField(
        max_digits=10, decimal_places=2, required=False,
        widget=forms.TextInput(attrs={'class': 'form-control autonumeric'})
    )
    mean_weight_per_cow_producer_kg = BrazilianDecimalField(
        max_digits=10, decimal_places=2, required=False,
        widget=forms.TextInput(attrs={'class': 'form-control autonumeric'})
    )
    mean_weight_per_cow_slaughterhouse_kg = BrazilianDecimalField(
        max_digits=10, decimal_places=2, required=False,
        widget=forms.TextInput(attrs={'class': 'form-control autonumeric'})
    )
    yield_live_cow_pasture_producer_percent = BrazilianDecimalField(
        max_digits=5, decimal_places=2, required=False, # Use 5 para porcentagens se 3 dígitos inteiros + 2 decimais bastar
        widget=forms.TextInput(attrs={'class': 'form-control autonumeric'})
    )
    yield_live_cow_pasture_slaughterhouse_percent = BrazilianDecimalField(
        max_digits=5, decimal_places=2, required=False,
        widget=forms.TextInput(attrs={'class': 'form-control autonumeric'})
    )
    yield_butchered_cow_producer_percent = BrazilianDecimalField(
        max_digits=5, decimal_places=2, required=False,
        widget=forms.TextInput(attrs={'class': 'form-control autonumeric'})
    )
    yield_butchered_cow_slaughterhouse_percent = BrazilianDecimalField(
        max_digits=5, decimal_places=2, required=False,
        widget=forms.TextInput(attrs={'class': 'form-control autonumeric', 'readonly': True})
    )
    price_closed_per_arroba_producer = BrazilianDecimalField(
        max_digits=10, decimal_places=2, required=False,
        widget=forms.TextInput(attrs={'class': 'form-control autonumeric'})
    )
    price_closed_per_arroba_slaughterhouse = BrazilianDecimalField(
        max_digits=10, decimal_places=2, required=False,
        widget=forms.TextInput(attrs={'class': 'form-control autonumeric'})
    )
    price_net_per_arroba_producer = BrazilianDecimalField(
        max_digits=10, decimal_places=2, required=False,
        widget=forms.TextInput(attrs={'class': 'form-control autonumeric'})
    )
    price_net_per_arroba_slaughterhouse = BrazilianDecimalField(
        max_digits=10, decimal_places=2, required=False,
        widget=forms.TextInput(attrs={'class': 'form-control autonumeric'})
    )
    price_per_kg_butchered_cow_producer = BrazilianDecimalField(
        max_digits=10, decimal_places=2, required=False,
        widget=forms.TextInput(attrs={'class': 'form-control autonumeric'})
    )
    price_per_kg_butchered_cow_slaughterhouse = BrazilianDecimalField(
        max_digits=10, decimal_places=2, required=False,
        widget=forms.TextInput(attrs={'class': 'form-control autonumeric'})
    )
    price_per_kg_after_butchered_cow_producer = BrazilianDecimalField(
        max_digits=10, decimal_places=2, required=False,
        widget=forms.TextInput(attrs={'class': 'form-control autonumeric'})
    )
    price_per_kg_after_butchered_cow_slaughterhouse = BrazilianDecimalField(
        max_digits=10, decimal_places=2, required=False,
        widget=forms.TextInput(attrs={'class': 'form-control autonumeric'})
    )
    slaughter_service_per_cow_producer = BrazilianDecimalField(
        max_digits=10, decimal_places=2, required=False,
        widget=forms.TextInput(attrs={'class': 'form-control autonumeric'})
    )
    slaughter_service_per_cow_slaughterhouse = BrazilianDecimalField(
        max_digits=10, decimal_places=2, required=False,
        widget=forms.TextInput(attrs={'class': 'form-control autonumeric'})
    )
    freight_producer_slaughterhouse_producer = BrazilianDecimalField(
        max_digits=6, decimal_places=2, required=False,
        widget=forms.TextInput(attrs={'class': 'form-control autonumeric'})
    )
    freight_slaughterhouse_store_producer = BrazilianDecimalField(
        max_digits=6, decimal_places=2, required=False,
        widget=forms.TextInput(attrs={'class': 'form-control autonumeric'})
    )
    freight_slaughterhouse_store_slaughterhouse = BrazilianDecimalField(
        max_digits=6, decimal_places=2, required=False,
        widget=forms.TextInput(attrs={'class': 'form-control autonumeric'})
    )
    commission_buyer = BrazilianDecimalField(
        max_digits=10, decimal_places=2, required=False,
        widget=forms.TextInput(attrs={'class': 'form-control autonumeric economia-input', 'readonly': True})
    )
    total_slaughter_cost = BrazilianDecimalField(
        max_digits=10, decimal_places=2, required=False,
        widget=forms.TextInput(attrs={'class': 'form-control autonumeric economia-input', 'readonly': True})
    )
    total_value_producer = BrazilianDecimalField(
        max_digits=12, decimal_places=2, required=False,
        widget=forms.TextInput(attrs={'class': 'form-control autonumeric economia-input', 'readonly': True})
    )
    total_value_slaughterhouse = BrazilianDecimalField(
        max_digits=12, decimal_places=2, required=False,
        widget=forms.TextInput(attrs={'class': 'form-control autonumeric economia-input', 'readonly': True})
    )
    profit_gain_comparison = BrazilianDecimalField(
        max_digits=12, decimal_places=2, required=False,
        widget=forms.TextInput(attrs={'class': 'form-control autonumeric economia-input', 'readonly': True})
    )

    # Campos que você definiu explicitamente no forms.py e que NÃO estão no seu models.py.
    # Ajustei o max_digits para 12 para acomodar valores maiores.
    granted_credit_percent = BrazilianDecimalField(
        max_digits=12, decimal_places=2, required=False, label="Crédito Outorgado (%)",
        widget=forms.TextInput(attrs={'class': 'form-control autonumeric', 'inputmode': 'decimal', 'readonly': True})
    )
    icms_debit_producer = BrazilianDecimalField(
        max_digits=12, decimal_places=2, required=False, label="ICMS Débito Produtor",
        widget=forms.TextInput(attrs={'class': 'form-control autonumeric', 'readonly': True, 'inputmode': 'decimal'})
    )
    icms_debit_slaughterhouse = BrazilianDecimalField(
        max_digits=12, decimal_places=2, required=False, label="ICMS Débito Frigorífico",
        widget=forms.TextInput(attrs={'class': 'form-control autonumeric', 'readonly': True})
    )
    icms_credit_slaughterhouse = BrazilianDecimalField(
        max_digits=12, decimal_places=2, required=False, label="ICMS Crédito Frigorífico",
        widget=forms.TextInput(attrs={'class': 'form-control autonumeric', 'readonly': True})
    )
    icms_loss_reversal_percent = BrazilianDecimalField(
        max_digits=12, decimal_places=2, required=False, label="Estorno ICMS da Perda (%)",
        widget=forms.TextInput(attrs={'class': 'form-control autonumeric', 'readonly': True})
    )
    protege_percent = BrazilianDecimalField(
        max_digits=12, decimal_places=2, required=False, label="PROTEGE (%)",
        widget=forms.TextInput(attrs={'class': 'form-control autonumeric', 'readonly': True})
    )
    fundeinfra_percent = BrazilianDecimalField(
        max_digits=12, decimal_places=2, required=False, label="FUNDEINFRO (%)",
        widget=forms.TextInput(attrs={'class': 'form-control autonumeric', 'readonly': True})
    )
    tax_producer_real = BrazilianDecimalField(
        max_digits=12, decimal_places=2, required=False, label="Imposto Efetivo Produtor (R$)",
        widget=forms.TextInput(attrs={'class': 'form-control autonumeric', 'readonly': True})
    )
    tax_slaughterhouse_real = BrazilianDecimalField(
        max_digits=12, decimal_places=2, required=False, label="Imposto Efetivo Frigorífico",
        widget=forms.TextInput(attrs={'class': 'form-control autonumeric', 'readonly': True})
    )
    tax_producer_percent = BrazilianDecimalField(
        max_digits=12, decimal_places=2, required=False, label="Imposto Efetivo Produtor (%)",
        widget=forms.TextInput(attrs={'class': 'form-control autonumeric', 'readonly': True})
    )
    tax_slaughterhouse_percent = BrazilianDecimalField(
        max_digits=12, decimal_places=2, required=False, label="Imposto Efetivo Frigorífico (%)",
        widget=forms.TextInput(attrs={'class': 'form-control autonumeric', 'readonly': True})
    )
    profit_producer_real = BrazilianDecimalField(
        max_digits=12, decimal_places=2, required=False, label="Margem de Lucro Produtor (R$)",
        widget=forms.TextInput(attrs={'class': 'form-control autonumeric', 'readonly': True})
    )
    profit_slaughterhouse_real = BrazilianDecimalField(
        max_digits=12, decimal_places=2, required=False, label="Margem de Lucro Frigorífico (R$)",
        widget=forms.TextInput(attrs={'class': 'form-control autonumeric', 'readonly': True})
    )
    profit_producer_percent = BrazilianDecimalField(
        max_digits=12, decimal_places=2, required=False, label="Margem de Lucro Produtor (%)",
        widget=forms.TextInput(attrs={'class': 'form-control autonumeric', 'readonly': True})
    )
    profit_slaughterhouse_percent = BrazilianDecimalField(
        max_digits=12, decimal_places=2, required=False, label="Margem de Lucro Frigorífico (%)",
        widget=forms.TextInput(attrs={'class': 'form-control autonumeric', 'readonly': True})
    )
    economia_mensal = BrazilianDecimalField(
        max_digits=12, decimal_places=2, required=False, label="Economia Mensal (R$)",
        widget=forms.TextInput(attrs={'class': 'form-control autonumeric economia-input', 'readonly': True})
    )
    economia_anual = BrazilianDecimalField(
        max_digits=12, decimal_places=2, required=False, label="Economia Anual (R$)",
        widget=forms.TextInput(attrs={'class': 'form-control autonumeric economia-input', 'readonly': True})
    )
    economia_arroba = BrazilianDecimalField(
        max_digits=12, decimal_places=2, required=False, label="Economia Arroba",
        widget=forms.TextInput(attrs={'class': 'form-control autonumeric economia-input', 'readonly': True})
    )
    economia_kg = BrazilianDecimalField(
        max_digits=12, decimal_places=2, required=False, label="Economia Kg",
        widget=forms.TextInput(attrs={'class': 'form-control autonumeric economia-input', 'readonly': True})
    )
    # Campos HiddenInput
    icms_debit_value = BrazilianDecimalField(required=False, widget=forms.HiddenInput())
    icms_credit_value = BrazilianDecimalField(required=False, widget=forms.HiddenInput())
    granted_credit_value = BrazilianDecimalField(required=False, widget=forms.HiddenInput())
    icms_loss_reversal_value = BrazilianDecimalField(required=False, widget=forms.HiddenInput())
    protege_value = BrazilianDecimalField(required=False, widget=forms.HiddenInput())
    fundeinfra_value = BrazilianDecimalField(required=False, widget=forms.HiddenInput())


    class Meta:
        model = MatrixSimulation
        exclude = ['user', 'created_at', 'updated_at']
        # Remova os widgets para os campos que você declarou explicitamente acima.
        # Eles já terão seus widgets definidos na declaração do campo.
        # Mantenha apenas os widgets para campos não-DecimalField ou campos que não foram explicitamente declarados.
        widgets = {
            'cow_weighing_location': forms.Select(attrs={'class': 'form-control select2 custom-select-bg'}),
            'description': forms.TextInput(attrs={'class': 'form-control'}) # Exemplo, se description não for BrazilianDecimalField
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Atualize as escolhas para 'cow_weighing_location'
        try:
            config = FieldConfiguration.objects.get(field_name='cow_weighing_location')
            options = FieldOption.objects.filter(field=config)
            self.fields['cow_weighing_location'].choices = [(opt.value, opt.label) for opt in options]
        except FieldConfiguration.DoesNotExist:
            self.fields['cow_weighing_location'].choices = [] # Garante que haja uma lista vazia se não encontrar


        # Carregamento de valores iniciais para campos ocultos
        # Isso ainda é feito aqui, pois BrazilianDecimalField não influencia o `initial`
        try:
            field_configs = {
                'icms_debit_percent': 'icms_debit_value',
                'icms_credit_percent': 'icms_credit_value',
                'granted_credit_percent': 'granted_credit_value',
                'icms_loss_reversal_percent': 'icms_loss_reversal_value',
                'protege_percent': 'protege_value',
                'fundeinfra_percent': 'fundeinfra_value',
            }

            for config_name, field_name in field_configs.items():
                config = FieldConfiguration.objects.get(field_name=config_name)
                option = FieldOption.objects.filter(field=config).first()
                if option:
                    # Converte para Decimal antes de definir o initial
                    # pois o valor da opção pode vir como string
                    self.fields[field_name].initial = BrazilianDecimalField().to_python(option.value)
        except FieldConfiguration.DoesNotExist as e:
            print(f"Configuração de campo não encontrada: {e}")
            # Lidar com o erro de forma apropriada, talvez definindo defaults ou logando.


    def clean(self):
        # Chama o clean do pai para garantir que a validação padrão dos campos ocorra.
        # Agora, todos os BrazilianDecimalFields já terão seus valores convertidos
        # para Decimal pelo método to_python deles.
        cleaned_data = super().clean()

        # Adicione aqui qualquer lógica de validação cruzada que você precisar
        # (validações que dependem de múltiplos campos)
        # Exemplo:
        # if 'campo_a' in cleaned_data and 'campo_b' in cleaned_data:
        #     if cleaned_data['campo_a'] > cleaned_data['campo_b']:
        #         self.add_error('campo_a', 'Campo A não pode ser maior que Campo B.')

        return cleaned_data