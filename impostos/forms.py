from django import forms
from impostos.models import (
    Cfop, 
    IcmsCst, 
    IcmsAliquota, 
    IcmsAliquotaReduzida, 
    CBENEF, 
    Protege, 
    PisCofinsCst, 
    NaturezaReceita,
    ReformaTributaria
)

class CfopForm(forms.ModelForm):
    class Meta:
        model = Cfop
        fields = ['cfop', 'description', 'operation']
        widgets = {
            'cfop': forms.NumberInput(attrs={'min': 1000, 'max': 9999}),
            'description': forms.TextInput(attrs={'placeholder': 'Descrição (opcional)'}),
            'operation': forms.Select(choices=[('E', 'Entrada'), ('S', 'Saída')]),
        }
        
class IcmsCstForm(forms.ModelForm):
    class Meta:
        model = IcmsCst
        fields = ['code', 'description']  
        
class IcmsAliquotaForm(forms.ModelForm):
    class Meta:
        model = IcmsAliquota
        fields = ['code', 'description']
        
class IcmsAliquotaReduzForm(forms.ModelForm):
    class Meta:
        model = IcmsAliquotaReduzida
        fields = ['code', 'description']
        
class CBENEFForm(forms.ModelForm):
    icms_cst = forms.ModelChoiceField(queryset=IcmsCst.objects.all(), empty_label="Selecione um ICMS CST")

    class Meta:
        model = CBENEF
        fields = ['code', 'icms_cst', 'description', 'legislation']  
        
class ProtegeForm(forms.ModelForm):
    class Meta:
        model = Protege
        fields = ['code', 'description']    
        
class PisCofinsCstForm(forms.ModelForm):
    pis_aliquota = forms.FloatField(
        widget=forms.NumberInput(attrs={
            'step': '0.01'
        })
    )
    
    cofins_aliquota = forms.FloatField(
        widget=forms.NumberInput(attrs={
            'step': '0.01'
        })
    )  
    
    type_company = forms.ChoiceField(
        choices=PisCofinsCst.DATA_TYPE_COMPANY_CHOICES,
        widget=forms.Select(attrs={
            'class': 'form-select'
        }),
        label='Classificação Fiscal'
    )      

    class Meta:
        model = PisCofinsCst
        fields = ['code', 'pis_aliquota', 'cofins_aliquota', 'description', 'type_company']   
        
class NaturezaReceitaForm(forms.ModelForm):
    piscofins_cst = forms.ModelChoiceField(queryset=PisCofinsCst.objects.all(), empty_label="Selecione um CST")

    description = forms.CharField(
        widget=forms.Textarea(attrs={
            'placeholder': 'Descrição detalhada',
            'rows': 4,
            'cols': 40
        })
    )  
    
    ncm = forms.CharField(
        widget=forms.Textarea(attrs={
            'placeholder': 'NCMs permitidos',
            'rows': 3,
            'cols': 40
        })
    )       
    
    class Meta:
        model = NaturezaReceita
        fields = ['code', 'description', 'ncm', 'piscofins_cst', 'category'] 
        widgets = {
            'category': forms.Select(choices=NaturezaReceita.CATEGORY_CHOICES)
        }                                      

class ReformaTributariaForm(forms.ModelForm):
    # Campos que se beneficiam de widgets Textarea para edição
    description_c_class_trib = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'placeholder': 'Descrição detalhada da Classificação Tributária',
            'rows': 4,
            'cols': 40
        })
    )  
    
    text_lc = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'placeholder': 'Texto integral ou referência da Lei Complementar',
            'rows': 3,
            'cols': 40
        })
    )       
    
    class Meta:
        model = ReformaTributaria
        # Incluímos todos os campos do modelo na Meta
        fields = [
            'cst_ibs_cbs', 
            'description_cst_ibs_cbs', 
            'c_class_trib', 
            'name_c_class_trib', 
            'description_c_class_trib', # Sobrescrito acima com Textarea
            'text_ec', 
            'text_lc', # Sobrescrito acima com Textarea
            'tipo_aliquota', 
            'aliquota_ibs', 
            'aliquota_cbs', 
            'p_red_aliq_ibs', 
            'p_red_aliq_cbs'
        ] 
        
        # Adicione placeholders para campos CharField/DecimalField que não usaram Textarea
        widgets = {
            'cst_ibs_cbs': forms.TextInput(attrs={'placeholder': 'CST IBS/CBS'}),
            'description_cst_ibs_cbs': forms.TextInput(attrs={'placeholder': 'Ex: Isento'}),
            'c_class_trib': forms.TextInput(attrs={'placeholder': 'Ex: 01.01.01'}),
            'name_c_class_trib': forms.TextInput(attrs={'placeholder': 'Nome da Classif. Tributária'}),
            'text_ec': forms.TextInput(attrs={'placeholder': 'Texto da EC'}),
            'tipo_aliquota': forms.TextInput(attrs={'placeholder': 'Tipo de Alíquota (ex: Padrão)'}),
            'aliquota_ibs': forms.NumberInput(attrs={'placeholder': 'Ex: 5.00', 'step': '0.01'}),
            'aliquota_cbs': forms.NumberInput(attrs={'placeholder': 'Ex: 5.00', 'step': '0.01'}),
            'p_red_aliq_ibs': forms.NumberInput(attrs={'placeholder': 'Ex: 60.00', 'step': '0.01'}),
            'p_red_aliq_cbs': forms.NumberInput(attrs={'placeholder': 'Ex: 60.00', 'step': '0.01'}),
        }
