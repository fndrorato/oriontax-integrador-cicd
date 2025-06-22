# from django import forms
# from pricing.models import ItemClass, Pricing
# from shopsim.models import SupplierProfile

# # Define as opções para os campos booleanos Sim/Não
# BOOLEAN_CHOICES = (
#     ('False', 'Não'),
#     ('True', 'Sim'),
# )

# class PricingForm(forms.ModelForm):
#     # Campos que se tornarão selects no template
#     item_class = forms.ModelChoiceField(
#         queryset=ItemClass.objects.filter(active=True),
#         label="Item:",
#         empty_label="Selecione a Classe do Item",
#         widget=forms.Select(attrs={'class': 'form-control'}) 
#     )
    
#     # Usando ChoiceField para forçar Sim/Não com seus valores de True/False
#     item_icms_excluded = forms.ChoiceField(
#         choices=BOOLEAN_CHOICES,
#         label="Produto está nas exceções do ICMS?",
#         widget=forms.Select(attrs={'class': 'form-control'})
#     )
#     items_pis_cofins_excluded = forms.ChoiceField(
#         choices=BOOLEAN_CHOICES,
#         label="Produto está nas exceções do PIS/COFINS?",
#         widget=forms.Select(attrs={'class': 'form-control'})
#     )

#     supplier = forms.ModelChoiceField(
#         queryset=SupplierProfile.objects.all(), # Ou SupplierProfile.objects.filter(active=True)
#         label="Fornecedor:",
#         empty_label="Selecione o Fornecedor",
#         widget=forms.Select(attrs={'class': 'form-control'})
#     )

#     # Campos que serão entrada de dados
#     markup = forms.CharField(widget=forms.TextInput())
#     card_tax = forms.CharField(widget=forms.TextInput())
#     cost_price = forms.CharField(widget=forms.TextInput())

#     sale_price_display = forms.CharField(
#         label="PREÇO DE VENDA =",
#         required=False,
#         widget=forms.TextInput(attrs={'class': 'form-control', 'readonly': 'readonly'})
#     )
    
#     # Campos para Créditos e Débitos (display only)
#     pis_credit_display = forms.CharField(
#         label="PIS",
#         required=False,
#         widget=forms.TextInput(attrs={'class': 'form-control', 'readonly': 'readonly'})
#     )
#     cofins_credit_display = forms.CharField(
#         label="COFINS",
#         required=False,
#         widget=forms.TextInput(attrs={'class': 'form-control', 'readonly': 'readonly'})
#     )
#     icms_credit_display = forms.CharField(
#         label="ICMS",
#         required=False,
#         widget=forms.TextInput(attrs={'class': 'form-control', 'readonly': 'readonly'})
#     )
#     pis_debit_display = forms.CharField(
#         label="PIS",
#         required=False,
#         widget=forms.TextInput(attrs={'class': 'form-control', 'readonly': 'readonly'})
#     )
#     cofins_debit_display = forms.CharField(
#         label="COFINS",
#         required=False,
#         widget=forms.TextInput(attrs={'class': 'form-control', 'readonly': 'readonly'})
#     )
#     icms_debit_display = forms.CharField(
#         label="ICMS",
#         required=False,
#         widget=forms.TextInput(attrs={'class': 'form-control', 'readonly': 'readonly'})
#     )

#     # Campos de Resultado (display only)
#     liquid_margin_value_display = forms.CharField(
#         label="Valor de Margem líquida",
#         required=False,
#         widget=forms.TextInput(attrs={'class': 'form-control', 'readonly': 'readonly'})
#     )
#     gross_margin_percentage_display = forms.CharField(
#         label="% de Margem Bruta",
#         required=False,
#         widget=forms.TextInput(attrs={'class': 'form-control', 'readonly': 'readonly'})
#     )
#     operational_cost_percentage_display = forms.CharField(
#         label="% Custo operacional",
#         required=False,
#         widget=forms.TextInput(attrs={'class': 'form-control', 'readonly': 'readonly'})
#     )
#     mark_down_percentage_display = forms.CharField(
#         label="% Mark Down",
#         required=False,
#         widget=forms.TextInput(attrs={'class': 'form-control', 'readonly': 'readonly'})
#     )
#     liquid_margin_final_percentage_display = forms.CharField(
#         label="% de Margem Líquida",
#         required=False,
#         widget=forms.TextInput(attrs={'class': 'form-control', 'readonly': 'readonly'})
#     )

#     class Meta:
#         model = Pricing
#         # Inclua todos os campos do model que você QUER que o formulário manipule diretamente.
#         # Campos calculados que não são salvos no model (como os _display) não precisam estar aqui.
#         fields = [
#             'description', 'item_class', 'item_icms_excluded', 'items_pis_cofins_excluded',
#             'supplier', 'markup', 'card_tax', 'total_cost_at_moment', # total_cost_at_moment será preenchido via JS e salvo no backend
#             'cost_price', 'sale_price'
#         ]
#         widgets = {
#             'description': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Descrição da Precificação'}),
#             'total_cost_at_moment': forms.HiddenInput(), # Campo hidden para passar o custo total do JS para o Python
#         }
    
#     def __init__(self, *args, **kwargs):
#         super().__init__(*args, **kwargs)
#         # Se você tiver uma instância existente, pode popular os campos de display
#         if self.instance and self.instance.pk:
#             # Exemplo de como popular um campo de display se o valor estiver no model
#             # self.fields['cost_price_display'].initial = self.instance.cost_price 
#             pass # Para este formulário, a maioria dos displays será preenchida por JS

import re
from decimal import Decimal, InvalidOperation
from django import forms
from pricing.models import ItemClass, Pricing # Certifique-se de que Pricing está importado
from shopsim.models import SupplierProfile

# Seu BrazilianDecimalField
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
    item_class = forms.ModelChoiceField(
        queryset=ItemClass.objects.filter(active=True),
        label="Item:",
        empty_label="Selecione a Classe do Item",
        widget=forms.Select(attrs={'class': 'form-control'}) 
    )
    
    item_icms_excluded = forms.ChoiceField(
        choices=BOOLEAN_CHOICES,
        label="Produto está nas exceções do ICMS?",
        widget=forms.Select(attrs={'class': 'form-control'})
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

    # CAMPOS DE ENTRADA QUE SERÃO SALVOS NO MODEL E PRECISAM DE TRATAMENTO
    # Use BrazilianDecimalField para converter a string formatada para Decimal
    markup = BrazilianDecimalField(
        max_digits=5, # Ajuste conforme a precisão necessária para o markup
        decimal_places=2,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    card_tax = BrazilianDecimalField(
        max_digits=5, # Ajuste conforme a precisão necessária para a taxa
        decimal_places=2,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    
    # Supondo que 'cost_price' no seu modelo Pricing é o custo base que o usuário digita
    # e que vem do campo 'initial_product_cost_01/02' no template.
    # O nome do campo no formulário deve corresponder ao nome no modelo.
    # Se 'cost_price' no modelo é o "Preço de Custo" inicial, use-o aqui.
    # Se o campo no seu modelo for, por exemplo, 'initial_product_cost', então use esse nome.
    # Vou manter 'cost_price' como exemplo, mas você deve usar o nome exato do campo do MODELO.
    cost_price = BrazilianDecimalField( # Este é o campo que recebe "R$ 17,00" do input do usuário
        max_digits=10, # Ajuste conforme o máximo esperado para preços
        decimal_places=2,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )

    # CAMPOS APENAS PARA EXIBIÇÃO NO FRONTEND (Calculados pelo JS)
    # Estes campos NÃO devem ser definidos explicitamente aqui se você não quer que eles sejam validados
    # ou salvos pelo form.ModelForm automaticamente. Eles são apenas para 'render_field'.
    # Eles serão populados pelo JS e seu conteúdo será ignorado ou recalcuado no backend.

    # Se você *realmente* precisa que esses valores calculados pelo JS sejam enviados
    # e validados pelo formulário (por exemplo, para auditoria, ou se não vai recalcular no backend),
    # então eles precisariam ser BrazilianDecimalField também, e você teria que incluí-los
    # no `Meta.fields` ou ajustar o `Meta.exclude`.
    # No entanto, a boa prática é recalcular no backend ou ter campos hidden para os valores brutos.

    # Para seguir a boa prática, vamos removê-los como campos explícitos do FORM,
    # exceto se você precisar deles para validação ou como campos de passagem.
    # Se eles são apenas 'display', eles não devem ser definidos aqui ou na Meta.fields.
    # Você os renderiza diretamente no template com {% render_field form.sale_price_display %}.

    # Exemplo: Se 'sale_price' é um campo REAL do seu MODELO 'Pricing'
    # e você quer que ele seja calculado e salvo no backend, NÃO o defina aqui como CharField ou BrazilianDecimalField
    # se o objetivo for que o formulário *não* o receba diretamente do POST.
    # Ele será preenchido no form_valid na view.
    # Se você quer receber o valor do JS e validá-lo:
    sale_price_display = BrazilianDecimalField( # Se você realmente quer validar este valor que vem do JS
        max_digits=10, decimal_places=2, required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'readonly': 'readonly'})
    )
    
    # Vou manter os campos de display como CharField SOMENTE SE você estiver usando
    # `render_field` neles e não estiver esperando que o form os valide ou salve.
    # Se eles são para salvar, use BrazilianDecimalField e inclua no Meta.fields.
    # PARA SIMPLIFICAR, ESTOU ASSUMINDO QUE OS "_DISPLAY" SÃO APENAS PARA O FRONTEND E NÃO SÃO SALVOS DIRETAMENTE.
    # Se forem para salvar, eles teriam que ter nomes no Model (ex: `pis_credit_value`, `gross_margin_percentage`)
    # e serem BrazilianDecimalField aqui.

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
    operational_cost_percentage_display = forms.CharField(required=False, widget=forms.TextInput(attrs={'class': 'form-control', 'readonly': 'readonly'}))
    mark_down_percentage_display = forms.CharField(required=False, widget=forms.TextInput(attrs={'class': 'form-control', 'readonly': 'readonly'}))
    liquid_margin_final_percentage_display = forms.CharField(required=False, widget=forms.TextInput(attrs={'class': 'form-control', 'readonly': 'readonly'}))

    # Campo para a descrição da simulação (do seu QueryDict)
    description = forms.CharField(
        label="Descrição:",
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Descrição da Precificação'}),
        required=True # Assumindo que a descrição é obrigatória
    )

    # Campo hidden para o custo total se você estiver passando-o do JS para o Python
    # e quiser salvá-lo como 'total_cost_at_moment' no seu modelo 'Pricing'.
    # Este campo DEVE ter um nome que corresponda a um campo no seu modelo Pricing.
    # O valor que ele recebe precisa ser limpo se vier formatado.
    # Se ele vem como um número puro do JS, um forms.DecimalField simples pode bastar.
    total_cost_at_moment = BrazilianDecimalField( # Supondo que ele também venha formatado
        max_digits=10, decimal_places=2, required=False,
        widget=forms.HiddenInput()
    )
    
    # Campos que correspondem diretamente aos campos do modelo Pricing (ex: `sale_price` no modelo)
    # Se `sale_price` é um campo do seu modelo e você quer que o valor calculado pelo JS seja salvo nele:
    # 1. Certifique-se de que o JS está enviando o valor para um campo `name="sale_price"` no HTML.
    # 2. Use BrazilianDecimalField se o JS estiver enviando-o formatado.
    sale_price = BrazilianDecimalField( # Este é o campo que será salvo no MODELO Pricing
        max_digits=10, decimal_places=2, required=False, # Ajuste required conforme seu modelo
        widget=forms.HiddenInput() # Pode ser hidden se não quiser que o usuário edite
    )
    # Você precisará de campos semelhantes para todos os resultados que deseja salvar,
    # como `liquid_margin_value`, `gross_margin_percentage`, etc.
    # Crie-os aqui como `BrazilianDecimalField` e defina-os como `HiddenInput()` se forem outputs calculados.


    class Meta:
        model = Pricing
        # Inclua APENAS os campos do modelo Pricing que são ENTRADA DO USUÁRIO
        # ou que serão CALCULADOS e SALVOS no backend a partir de ENTRADAS/CÁLCULOS do FORM.
        # Não inclua campos que são puramente "display" no frontend se eles não forem salvos no modelo.
        fields = [
            'description',
            'item_class',
            'item_icms_excluded',
            'items_pis_cofins_excluded',
            'supplier',
            'markup',
            'card_tax',
            'cost_price', # Este é o custo base que o usuário informa
            'total_cost_at_moment', # Se você quiser salvar o total_cost_at_moment que vem do JS
            'sale_price', # Se você quer salvar o sale_price calculado pelo JS
            # Adicione outros campos do modelo Pricing que você deseja salvar aqui:
            # 'liquid_margin_value',
            # 'gross_margin_percentage',
            # etc.
        ]
        # Se você tiver campos no seu modelo Pricing para cada resultado final (ex: liquid_margin_value, gross_margin_percentage),
        # você precisará adicioná-los no `fields` acima e no HTML como campos hidden ou readonly.
        # No POST, eles viriam com a formatação e seriam tratados pelo BrazilianDecimalField.

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Ajuste a label para 'description' para coincidir com o HTML
        self.fields['description'].label = "Descrição da Simulação:"

        # Se você está usando initial para 'operational_cost_percentage_display' na view,
        # ele será preenchido aqui.
        # No entanto, como ele é um campo "display only" e não está no Meta.fields,
        # ele não será salvo. Se você precisa salvá-lo, crie um campo correspondente
        # no seu modelo Pricing e inclua-o no Meta.fields.
        # Por enquanto, vou deixá-lo como CharField para display no template.

        # Campos de "display" não precisam ser tratados aqui se não forem campos do Meta.fields
        # e forem apenas para o frontend.
        # Certifique-se que o seu JS AutoNumeric está formatando o campo `cost_price`
        # no template para `R$ 17,00`, pois este é o campo de entrada.
        # Os campos `_display` (como `sale_price_display`) devem ser manipulados
        # apenas pelo JS e não precisam de validação ou processamento aqui se não forem salvos.

    def clean_item_icms_excluded(self):
        # Converte a string 'True'/'False' para booleano
        value = self.cleaned_data['item_icms_excluded']
        return value == 'True'

    def clean_items_pis_cofins_excluded(self):
        # Converte a string 'True'/'False' para booleano
        value = self.cleaned_data['items_pis_cofins_excluded']
        return value == 'True'

    # Não adicione métodos clean_ para os campos _display se eles não estiverem no Meta.fields,
    # pois eles não serão processados pelo formulário.
    # Se você decidir incluí-los no Meta.fields, adicione o `clean_` correspondente e use
    # BrazilianDecimalField para eles também.