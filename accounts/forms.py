# forms.py
from django import forms
from django.contrib.auth.models import User, Group
from .models import Profile
from django.core.exceptions import ValidationError
from django.utils import timezone

def generate_temporary_password(length=10):
    import random
    import string
    characters = string.ascii_letters + string.digits
    return ''.join(random.choice(characters) for i in range(length))

# def validate_birth_date(value):
#     if value > timezone.now().date():
#         raise ValidationError("The birth date cannot be in the future.")

class SignUpForm(forms.ModelForm):
    first_name = forms.CharField(max_length=50, required=True, widget=forms.TextInput(attrs={'class': 'form-control'}))
    last_name = forms.CharField(max_length=50, required=True, widget=forms.TextInput(attrs={'class': 'form-control'}))
    email = forms.EmailField(max_length=254, required=True, help_text='Required. Enter a valid email address.', widget=forms.EmailInput(attrs={'class': 'form-control'}))    
    birth_date = forms.DateField(
        help_text='Required. Format: dd/mm/yyyy',
        widget=forms.DateInput(attrs={'class': 'form-control date', 'data-mask': '99/99/9999', 'placeholder': 'dd/mm/yyyy'}),
        input_formats=['%d/%m/%Y']
    )    
    phone = forms.CharField(max_length=17, required=False, widget=forms.TextInput(attrs={'class': 'form-control telphone_with_code', 'data-mask':'(99) 99999-9999'}))
    groups = forms.ModelChoiceField(queryset=Group.objects.all(), required=True, widget=forms.Select(attrs={'class': 'form-control'}))
    class Meta:
        model = User
        fields = ('first_name', 'last_name', 'email', 'birth_date', 'phone', 'groups')
        
    def validate_birth_date(self):
        birth_date = self.cleaned_data.get('birth_date')
        if birth_date > timezone.now().date():
            self.add_error('birth_date', 'A data de nascimento não pode ser no futuro.')
        return birth_date
        

    def save(self, commit=True):
        user = super().save(commit=False)
        user.username = user.email
        password = generate_temporary_password()
        user.set_password(password)
        if commit:
            user.save()
            profile, created = Profile.objects.get_or_create(user=user, defaults={'birth_date': self.cleaned_data['birth_date'], 'phone': self.cleaned_data['phone']})
            if not created:
                profile.birth_date = self.cleaned_data['birth_date']
                profile.phone = self.cleaned_data['phone']
                profile.save()
            user.groups.set([self.cleaned_data['groups']])  # Set user to the single selected group
        return user
    
class UserModelForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ('first_name', 'last_name', 'email', 'is_active')
        
    def __init__(self, *args, **kwargs):
        self.instance = kwargs.get('instance', None)
        super(UserModelForm, self).__init__(*args, **kwargs)
                
    def clean_email(self):
        email = self.cleaned_data['email']
        # Check if email already exists in the database
        if User.objects.filter(email=email).exclude(pk=self.instance.pk).exists():
            raise forms.ValidationError('Este email já está em uso.')

        return email 
    
    def save(self, commit=True):
        user = super(UserModelForm, self).save(commit=False)
        # username and password will be set in the view
        if commit:
            user.save()
        return user           
        
class ProfileForm(forms.ModelForm):
    class Meta:
        model = Profile
        fields = ('birth_date', 'phone', 'supervisor', 'manager')
        
    def __init__(self, *args, **kwargs):
        super(ProfileForm, self).__init__(*args, **kwargs)
        supervisor_users = User.objects.filter(groups__name='supervisor')
        print("Supervisor users:", supervisor_users)  # Verifique se está retornando usuários
        manager_users = User.objects.filter(groups__name='gerente')
        print("Manager users:", manager_users)  # Verifique se está retornando usuários
        self.fields['supervisor'].queryset = supervisor_users
        self.fields['manager'].queryset = manager_users       

    def clean_birth_date(self):
        birth_date = self.cleaned_data.get('birth_date')
        if birth_date:
            if birth_date > timezone.now().date():
                self.add_error('birth_date', 'A data de nascimento não pode ser no futuro.')
        
        return birth_date 
        
    
