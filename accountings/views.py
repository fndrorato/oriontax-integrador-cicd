from rolepermissions.decorators import has_role_decorator
from django.shortcuts import render, redirect
from urllib.parse import urlencode
from django.views.generic import CreateView, ListView, UpdateView, DeleteView
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.urls import reverse_lazy, path
from .models import Accounting
from .forms import AccountingForm

@method_decorator(login_required(login_url='login'), name='dispatch')
class AccountingsListView(ListView):
    model = Accounting
    template_name = 'list_accountings.html'
    context_object_name = 'accountings'

@method_decorator(has_role_decorator(['administrador', 'gerente']), name='dispatch')    
class NewAccountingCreateView(CreateView):
    model = Accounting
    form_class = AccountingForm
    template_name = 'create_accounting.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        message = self.request.GET.get('success')
        context['message'] = message   
        return context       
    
    def get_success_url(self):
        success_url = reverse_lazy('create_accounting')  # Assuming you have a URL named 'contabilidades'
        message = urlencode({'success': 'Contabilidade criada com sucesso!'})  # URL-encode message for safety
        return f"{success_url}?{message}"

    def form_valid(self, form):
        self.object = form.save()
        return redirect(self.get_success_url())   
   
@method_decorator(login_required(login_url='login'), name='dispatch')
# @method_decorator(has_role_decorator(['administrador', 'gerente']), name='dispatch')    
class AccountingUpdateView(UpdateView):
    model = Accounting
    form_class = AccountingForm
    template_name = 'update_accounting.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        accounting = self.get_object()
        context['city'] = accounting.city   
        return context 
    
    def get_success_url(self):
        return reverse_lazy('update_accounting', kwargs={'pk': self.object.pk}) 