from rolepermissions.decorators import has_role_decorator
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.urls import reverse_lazy
from django.views.generic import CreateView, ListView, UpdateView, DeleteView
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from .models import ERP
from .forms import ERPForm

@method_decorator(login_required(login_url='login'), name='dispatch')
class ErpsListView(ListView):
    model = ERP
    template_name = 'list_erps.html'
    context_object_name = 'erps'
    
@method_decorator(login_required(login_url='login'), name='dispatch')
@method_decorator(has_role_decorator(['administrador', 'gerente']), name='dispatch')
class NewErpCreateView(CreateView):
    model = ERP
    form_class = ERPForm
    template_name = 'create_erp.html'
    success_url = '/sistemas/'  

@method_decorator(login_required(login_url='login'), name='dispatch')
class ErpUpdateView(UpdateView):
    model = ERP
    form_class = ERPForm
    template_name = 'update_erp.html'
    
    # nova forma de redirecionamento para o usuario
    # abaixo é uma success url personalizada
    def get_success_url(self):
        return reverse_lazy('erp_update', kwargs={'pk': self.object.pk})  
    
@method_decorator(login_required(login_url='login'), name='dispatch')
@method_decorator(has_role_decorator(['administrador', 'gerente']), name='dispatch')
class ErpDeleteView(DeleteView):
    model = ERP
    template_name = 'update_erp.html'
    success_url = reverse_lazy('erps_list')

    def get_object(self, queryset=None):
        return get_object_or_404(ERP, pk=self.kwargs['pk'])

    def delete(self, request, *args, **kwargs):
        try:
            response = super().delete(request, *args, **kwargs)
            messages.success(request, "ERP deleted successfully.")
            return redirect('erps_list')
        except (ObjectDoesNotExist, ValidationError) as e:
            messages.error(request, f"Error deleting ERP: {e}")
            return redirect('erp_update', pk=self.kwargs['pk'])     