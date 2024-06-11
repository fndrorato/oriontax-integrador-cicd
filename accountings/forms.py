from django import forms
from clients.models import Cities
from .models import Accounting

class AccountingForm(forms.ModelForm):
    class Meta:
        model = Accounting
        fields = ['name', 'city', 'email', 'phone', 'contact']  
        
    def __init__(self, *args, **kwargs):
        super(AccountingForm, self).__init__(*args, **kwargs)
        # Ordena o campo 'city' pelo nome
        self.fields['city'].queryset = Cities.objects.all().order_by('nome') 