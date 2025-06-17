import re
from decimal import Decimal
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import render, get_object_or_404, redirect
from django.utils.decorators import method_decorator
from django.views import View
from django.http import JsonResponse
from django.views.generic import ListView, UpdateView
from django.views.generic.edit import CreateView, DeleteView
from django.urls import reverse_lazy
from rolepermissions.decorators import has_role_decorator
from cattles.models import (
    MatrixSimulation, ButcheryMaster, ButcheryDetail, MeatCut, UserMeatCut
)
from cattles.forms import MatrixSimulationForm


class MatrixSimulationListView(LoginRequiredMixin, ListView):
    model = MatrixSimulation
    template_name = 'list_simulation_cattle.html'  # mesmo nome do template criado
    context_object_name = 'simulations'
    ordering = ['-created_at']

    def get_queryset(self):
        return MatrixSimulation.objects.filter(user=self.request.user) 
 
@method_decorator(login_required(login_url='login'), name='dispatch')
class MatrixSimulationCreateView(CreateView):
    model = MatrixSimulation
    form_class = MatrixSimulationForm
    template_name = 'create_simulation_cattle.html'
    success_url = '/cattles/simulation/'

    def form_valid(self, form):
        print("📦 Dados brutos (POST):", self.request.POST)
        print("✅ Dados limpos (cleaned_data):", form.cleaned_data)        

        instance = form.save(commit=False)
        instance.user = self.request.user
        instance.description = self.request.POST.get("description")
        instance.save()

        return super().form_valid(form)

    def form_invalid(self, form):
        print("📦 Dados brutos (POST):", self.request.POST)        
        print("❌ Formulário inválido!")
        print(form.errors)  # Mostra os erros que impedem a validação
        return super().form_invalid(form)    

class MatrixSimulationUpdateView(LoginRequiredMixin, UpdateView):
    model = MatrixSimulation
    form_class = MatrixSimulationForm
    template_name = 'create_simulation_cattle.html'  # reutiliza o mesmo template do CreateView
    success_url = reverse_lazy('simulation_list')

    def get_queryset(self):
        # Garante que o usuário só possa editar suas próprias simulações
        return MatrixSimulation.objects.filter(user=self.request.user)

    def form_valid(self, form):
        form.instance.user = self.request.user
        return super().form_valid(form)
    
class MatrixSimulationDeleteView(LoginRequiredMixin, DeleteView):
    model = MatrixSimulation
    template_name = 'confirm_delete_simulation.html'
    success_url = reverse_lazy('simulation_list')

    def get_queryset(self):
        # Garante que o usuário só possa excluir suas próprias simulações
        return MatrixSimulation.objects.filter(user=self.request.user)

class UpdateButcheryView(LoginRequiredMixin, View):
    template_name = 'butchery_update.html'

    def get(self, request):
        master = get_object_or_404(ButcheryMaster, user=request.user)
        details = ButcheryDetail.objects.filter(butchery=master)
        user_cuts = UserMeatCut.objects.filter(user=request.user).order_by('meat_cut')
        cuts_json = list(user_cuts.values_list('meat_cut', flat=True))  # para autocomplete

        context = {
            'master': master,
            'details': details,
            'available_cuts': user_cuts,
            'cuts_json': cuts_json,
        }
        print(context)
        return render(request, self.template_name, context)

    def post(self, request, pk):
        master = get_object_or_404(ButcheryMaster, pk=pk, user=request.user)
        master.arroba_price_nf = request.POST.get('arroba_price_nf')
        master.invoice_weight = request.POST.get('invoice_weight')
        master.cost_per_kg = request.POST.get('cost_per_kg')
        master.save()

        # Apaga os detalhes antigos do usuário
        ButcheryDetail.objects.filter(user_meat_cut__user=request.user).delete()

        # Processa os cortes enviados
        index = 0
        while True:
            name = request.POST.get(f'cuts[{index}][name]')
            weight = request.POST.get(f'cuts[{index}][weight]')
            price = request.POST.get(f'cuts[{index}][selling_price]')

            if name is None:
                break  # termina o loop quando não há mais entradas

            user_cut, _ = UserMeatCut.objects.get_or_create(user=request.user, meat_cut=name)

            ButcheryDetail.objects.create(
                user_meat_cut=user_cut,
                selling_price=price,
            )
            index += 1

        return redirect('update_butchery', pk=master.pk)

class CreateMeatCutView(LoginRequiredMixin, View):
    def post(self, request):
        name = request.POST.get('name')
        
        if not name:
            return JsonResponse({'error': 'Nome do corte é obrigatório.'}, status=400)

        # Cria o corte para o usuário, se ainda não existir
        user_cut, created = UserMeatCut.objects.get_or_create(
            user=request.user,
            meat_cut=name
        )

        return JsonResponse({
            'id': user_cut.id,
            'name': name,
            'message': 'Corte criado com sucesso.'
        }, status=201)

