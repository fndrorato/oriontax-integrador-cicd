from django import forms
from .models import ERP

class ERPForm(forms.ModelForm):
    class Meta:
        model = ERP
        fields = ['name', 'description', 'method_integration', 'periodicity']
