from django import forms
from .models import Cfop, IcmsCst, IcmsAliquota, IcmsAliquotaReduzida, CBENEF, Protege, PisCofinsCst, NaturezaReceita

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

    class Meta:
        model = PisCofinsCst
        fields = ['code', 'pis_aliquota', 'cofins_aliquota', 'description']   
        
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
