from django import forms
from django.core.exceptions import ValidationError
from .models import Item
from impostos.models import IcmsAliquota, IcmsAliquotaReduzida, Protege, CBENEF, PisCofinsCst, NaturezaReceita, Cfop


class ItemForm(forms.ModelForm):
    icms_aliquota_reduzida = forms.ChoiceField(
        choices=[],  # Deixe as escolhas vazias inicialmente
        widget=forms.Select,
    )
        
        
    class Meta:
        model = Item
        fields = [
            'client', 'code', 'barcode', 'description', 'ncm', 'cfop', 'icms_cst', 'icms_aliquota',
            'icms_aliquota_reduzida', 'protege', 'cbenef', 'piscofins_cst', 'pis_aliquota',
            'cofins_aliquota', 'naturezareceita', 'cest'
        ]
        widgets = {
            'icms_aliquota': forms.Select(),
            'protege': forms.Select(),
            'cbenef': forms.Select(),
            'piscofins_cst': forms.Select(),
            'naturezareceita': forms.Select()
        }  
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['icms_aliquota'].queryset = IcmsAliquota.objects.all()
        self.fields['protege'].queryset = Protege.objects.all()
        self.fields['cbenef'].queryset = CBENEF.objects.all()
        self.fields['piscofins_cst'].queryset = PisCofinsCst.objects.all()
        self.fields['naturezareceita'].queryset = NaturezaReceita.objects.all() 
        
        choices = [('', '---------')] + [(str(ia.code), str(ia.code)) for ia in IcmsAliquota.objects.all()]
        self.fields['icms_aliquota_reduzida'].choices = choices       
        
    def clean_cest(self):
        cest = self.cleaned_data.get('cest', '')
        if cest and len(cest) != 7:
            raise ValidationError("O campo CEST deve ter exatamente 7 dígitos.")
        return cest

    def clean_ncm(self):
        ncm = self.cleaned_data.get('ncm', '')
        if len(ncm) != 8:
            raise ValidationError("O campo NCM deve ter exatamente 8 dígitos.")
        return ncm  
    
    def clean_icms_aliquota_reduzida(self):
        icms_cst = str(self.cleaned_data.get('icms_cst'))
        icms_aliquota_reduzida = self.data.get('icms_aliquota_reduzida')
        icms_aliquota = self.cleaned_data.get('icms_aliquota')
        choices = [str(choice[0]) for choice in self.fields['icms_aliquota_reduzida'].choices]

        # Verifica se o valor está nas opções ou é igual ao icms_aliquota
        if icms_cst == '20':
            if str(icms_aliquota_reduzida) not in choices:
                print(choices)
                raise ValidationError(f'O valor do ICMS Alíquota Reduzida({icms_aliquota_reduzida}) deve ser uma das opções disponíveis quando ICMS CST é 20.')
        else:
            if str(icms_aliquota_reduzida) != str(icms_aliquota):  # Converte icms_aliquota para string
                raise ValidationError(f'ICMS Alíquota Reduzida ({icms_aliquota_reduzida}) deve ser igual a ICMS Alíquota ({icms_aliquota}) quando ICMS CST não for 20. IcmsCST: {icms_cst}')

        return icms_aliquota_reduzida

    def clean(self):
        print("Entrou no método clean do formulário.")  # Adicione este print 
        cleaned_data = super().clean()
        icms_aliquota_reduzida = self.data.get('icms_aliquota_reduzida')
        if icms_aliquota_reduzida:
            cleaned_data['icms_aliquota_reduzida'] = icms_aliquota_reduzida
     
        client = cleaned_data.get("client")
        code = cleaned_data.get("code")        
        cfop = cleaned_data.get('cfop')
        # Validação final do icms_aliquota_reduzida após a limpeza
        icms_cst = self.cleaned_data.get('icms_cst')
        icms_aliquota_reduzida = self.cleaned_data.get('icms_aliquota_reduzida')  # Usa cleaned_data
        icms_aliquota = self.cleaned_data.get('icms_aliquota')
        choices = [str(choice[0]) for choice in self.fields['icms_aliquota_reduzida'].choices]

        # if icms_cst == '20':
        #     if icms_aliquota_reduzida not in choices:
        #         raise ValidationError('O valor do ICMS Alíquota Reduzida deve ser uma das opções disponíveis quando ICMS CST é 20.')
        # else:
        #     if icms_aliquota_reduzida != str(icms_aliquota):
        #         raise ValidationError('ICMS Alíquota Reduzida deve ser igual a ICMS Alíquota quando ICMS CST não for 20.')

        cbenef = cleaned_data.get('cbenef')
        piscofins_cst = cleaned_data.get('piscofins_cst')
        naturezareceita = cleaned_data.get('naturezareceita')     

        if not self.instance.pk and Item.objects.filter(client=client, code=code).exists():
            self.add_error('code', 'Esse código já existe para essa cliente.')

        # Regra 1: CFOP 5405 só pode usar ICMS CST 60
        if cfop == 5405 and icms_cst != '60':
            self.add_error('icms_cst', 'Para CFOP 5405, o ICMS CST deve ser 60.')

        # Regra 2: Demais CFOPs não podem usar ICMS CST 60
        if cfop != 5405 and icms_cst == '60':
            self.add_error('icms_cst', 'O ICMS CST 60 só pode ser usado com CFOP 5405.')

        # Regra 6: Natureza Receita deve ser em branco se PIS CST for 01
        if piscofins_cst and piscofins_cst.code == '01' and naturezareceita:
            self.add_error('naturezareceita', 'Natureza Receita deve estar em branco quando PIS CST é 01.')

        print("Dados limpos:", cleaned_data)
        return cleaned_data
    
class CSVUploadForm(forms.Form):
    csv_file = forms.FileField()    
    