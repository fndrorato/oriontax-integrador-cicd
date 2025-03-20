from django import forms
from django.contrib.auth.models import User, Group
from erp.models import ERP
from accountings.models import Accounting
from django.utils import timezone
from .models import Client, Store, Cities

class ClientForm(forms.ModelForm):
    class Meta:
        model = Client
        fields = ['name', 'num_stores', 'date_contract', 'date_send', 'economic_benefit', 'erp', 
                  'accounting', 'commercial_responsible', 'owner', 'email', 'contact', 'user', 'is_active', 
                  'day_sent', 'first_load_date', 'connection_route', 'port_route', 'user_route', 'password_route', 
                  'database_route', 'cnpj', 'client_status', 'last_date_get', 'last_date_send']

    def __init__(self, *args, **kwargs):
        super(ClientForm, self).__init__(*args, **kwargs)
        # Ajuste os querysets com base no contexto
        self.fields['accounting'].queryset = Accounting.objects.all()
        self.fields['erp'].queryset = ERP.objects.all()
        analysts_group = Group.objects.get(name='analista')
        self.fields['user'].queryset = User.objects.filter(groups=analysts_group)      
        self.fields['day_sent'].choices = Client.DATA_SENT_CHOICES
        self.fields['client_status'].choices = Client.DATA_STATUS_CHOICES
        # Define o campo password_route como um campo de senha
        self.fields['password_route'].widget = forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Senha'
        })        
        
    def clean_date_contract(self):
        date_contract = self.cleaned_data.get('date_contract')
        if date_contract and date_contract > timezone.now().date():
            raise forms.ValidationError("A data informada não pode estar no futuro.")
        return date_contract

    def clean_date_send(self):
        date_send = self.cleaned_data.get('date_send')
        if date_send and date_send > timezone.now().date():
            raise forms.ValidationError("A data informada não pode estar no futuro.")
        return date_send   
    
class StoreForm(forms.ModelForm):
    class Meta:
        model = Store
        fields = ['corporate_name', 'city', 'cnpj', 'connection_route', 'is_active', 'client']  
        
    def __init__(self, *args, **kwargs):
        super(StoreForm, self).__init__(*args, **kwargs)
        # Ordena o campo 'city' pelo nome
        self.fields['city'].queryset = Cities.objects.all().order_by('nome')               
