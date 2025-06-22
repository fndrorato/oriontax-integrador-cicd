import json
import re
from decimal import Decimal
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.serializers.json import DjangoJSONEncoder
from django.db.models import Sum
from django.shortcuts import render, get_object_or_404, redirect
from django.utils.decorators import method_decorator
from django.views import View
from django.http import JsonResponse
from django.views.generic import ListView, UpdateView, TemplateView
from django.views.generic.edit import CreateView, DeleteView
from django.urls import reverse_lazy
from rolepermissions.decorators import has_role_decorator
from pricing.forms import PricingForm
from pricing.models import (
    UsersCosts, CostsMaster, CostsDetail, ItemClass, Pricing
)
from shopsim.models import SupplierProfile


class UpdateFixedExpensesView(LoginRequiredMixin, View):
    template_name = 'fixed_expenses.html'

    def get(self, request):
        master = get_object_or_404(CostsMaster, user=request.user)
        details = CostsDetail.objects.filter(costs_master=master)
        user_costs = UsersCosts.objects.filter(user=request.user).order_by('description')
        costs_json = list(user_costs.values_list('description', flat=True))  # para autocomplete

        context = {
            'master': master,
            'details': details,
            'available_costs': user_costs,
            'costs_json': costs_json,
        }

        return render(request, self.template_name, context)

    def post(self, request):
        master_id = request.POST.get('master_id')
        master = get_object_or_404(CostsMaster, pk=master_id, user=request.user)

        # Atualiza campos principais
        master.sales_per_month = request.POST.get('sales_per_month', '').replace('R$', '').replace('.', '').replace(',', '.').strip() or 0
        master.save()

        # Remove detalhes antigos
        master.costs_detail.all().delete()

        # Insere os novos detalhes
        index = 0
        while True:
            user_costs_id = request.POST.get(f'costs[{index}][user_costs_id]')
            value = request.POST.get(f'costs[{index}][value]', '').replace('R$', '').replace('.', '').replace(',', '.').strip()

            if user_costs_id is None:
                break

            if not all([user_costs_id, value]):
                index += 1
                continue  # pula se algum campo obrigatório estiver faltando

            try:
                user_costs = UsersCosts.objects.get(pk=user_costs_id, user=request.user)
            except UsersCosts.DoesNotExist:
                index += 1
                continue  # ignora se o corte não existir ou não for do usuário

            CostsDetail.objects.create(
                costs_master=master,
                user_costs=user_costs,
                value=value
            )

            index += 1

        return redirect('update_fixed_expenses')

class CreateCostsView(LoginRequiredMixin, View):
    def post(self, request):
        description = request.POST.get('description')
        
        if not description:
            return JsonResponse({'error': 'Descrição do custo é obrigatório.'}, status=400)

        # Cria o corte para o usuário, se ainda não existir
        user_cut, created = UsersCosts.objects.get_or_create(
            user=request.user,
            description=description
        )

        return JsonResponse({
            'id': user_cut.id,
            'name': description,
            'message': 'Custo criado com sucesso.'
        }, status=201)

# class PricingView(LoginRequiredMixin, View):
#     template_name = 'pricing_simulation.html'
#     success_url = reverse_lazy('simulation_shop_list')
    
#     def get(self, request, *args, **kwargs):
#         master = get_object_or_404(CostsMaster, user=request.user)
#         details = CostsDetail.objects.filter(costs_master=master)        

#         # --- Cálculo da porcentagem de custo operacional
#         total_value = details.aggregate(total=Sum('value'))['total'] or 0
#         sales_per_month = master.sales_per_month or 1  # evita divisão por zero
#         porcentagem_custo_operacional = (total_value / sales_per_month) * 100

#         # Inicializa o formulário com o valor calculado
#         form = PricingForm(initial={
#             'operational_cost_percentage_display': round(porcentagem_custo_operacional, 2)
#         })

#         # Dados para JS
#         item_class_data = list(ItemClass.objects.filter(active=True).values('id', 'icms_value', 'pis_value', 'cofins_value'))
#         supplier_data = list(SupplierProfile.objects.all().values('id', 'tax_value'))

#         processed_item_class_data = {
#             str(item['id']): {
#                 'icms_value': float(item['icms_value']),
#                 'pis_value': float(item['pis_value']),
#                 'cofins_value': float(item['cofins_value']),
#             } for item in item_class_data
#         }

#         processed_supplier_data = {
#             str(supplier['id']): {
#                 'tax_value': float(supplier['tax_value']),
#             } for supplier in supplier_data
#         }

#         context = {
#             'form': form,
#             'item_class_json': json.dumps(processed_item_class_data),
#             'supplier_json': json.dumps(processed_supplier_data),
#             'porcentagem_custo_operacional': round(porcentagem_custo_operacional, 2),
#         }
#         return render(request, self.template_name, context)


#     def post(self, request, *args, **kwargs):
#         form = PricingForm(request.POST)
#         if form.is_valid():
#             pricing_instance = form.save(commit=False)
#             pricing_instance.user = request.user # Associa o usuário logado
            
#             # Alternativamente, recalcule no backend para maior segurança:
#             item_class = pricing_instance.item_class
#             markup = pricing_instance.markup
#             card_tax = pricing_instance.card_tax
#             cost_price = pricing_instance.cost_price
#             pricing_instance.save()
#             return redirect('success_url') # Redirecione para uma URL de sucesso ou a mesma página
        
#         # Se o formulário não for válido, renderize-o novamente com os erros
#         item_class_data = list(ItemClass.objects.filter(active=True).values('id', 'icms_value', 'pis_value', 'cofins_value'))
#         processed_item_class_data = {}
#         for item in item_class_data:
#             processed_item_class_data[str(item['id'])] = {
#                 'icms_value': float(item['icms_value']),
#                 'pis_value': float(item['pis_value']),
#                 'cofins_value': float(item['cofins_value']),
#             }

#         context = {
#             'form': form,
#             'item_class_json': json.dumps(processed_item_class_data),
#         }
#         return render(request, self.template_name, context)
class PricingListView(LoginRequiredMixin, ListView):
    model = Pricing
    template_name = 'list_pricing.html'  # mesmo nome do template criado
    context_object_name = 'pricings'
    ordering = ['-created_at']

    def get_queryset(self):
        return Pricing.objects.filter(user=self.request.user) 

class PricingCreateView(LoginRequiredMixin, CreateView):
    model = Pricing # Defina o modelo que o formulário está criando
    form_class = PricingForm
    template_name = 'pricing_simulation.html' # Confirme o nome do seu template
    success_url = reverse_lazy('simulation_shop_list') # Confirme o nome da sua URL de sucesso

    def get_initial(self):
        initial = super().get_initial()
        # Calcula a porcentagem de custo operacional para preencher o campo inicial
        master = get_object_or_404(CostsMaster, user=self.request.user)
        details = CostsDetail.objects.filter(costs_master=master)        

        total_value = details.aggregate(total=Sum('value'))['total'] or 0
        sales_per_month = master.sales_per_month or 1  # evita divisão por zero
        
        # Use Decimal para precisão nos cálculos financeiros
        porcentagem_custo_operacional = Decimal(total_value) / Decimal(sales_per_month) * 100

        initial['operational_cost_percentage_display'] = round(porcentagem_custo_operacional, 2)
        return initial

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Lógica para obter e processar dados do ItemClass e SupplierProfile para JS
        item_class_data = list(ItemClass.objects.filter(active=True).values('id', 'icms_value', 'pis_value', 'cofins_value'))
        supplier_data = list(SupplierProfile.objects.all().values('id', 'tax_value'))

        processed_item_class_data = {
            str(item['id']): {
                'icms_value': float(item['icms_value']), # Converte Decimal para float
                'pis_value': float(item['pis_value']),
                'cofins_value': float(item['cofins_value']),
            } for item in item_class_data
        }

        processed_supplier_data = {
            str(supplier['id']): {
                'tax_value': float(supplier['tax_value']), # Converte Decimal para float
            } for supplier in supplier_data
        }

        # Calcula a porcentagem de custo operacional novamente para o contexto, se necessário para exibição separada
        master = get_object_or_404(CostsMaster, user=self.request.user)
        details = CostsDetail.objects.filter(costs_master=master)        
        total_value = details.aggregate(total=Sum('value'))['total'] or 0
        sales_per_month = master.sales_per_month or 1
        porcentagem_custo_operacional = Decimal(total_value) / Decimal(sales_per_month) * 100

        context['item_class_json'] = json.dumps(processed_item_class_data, cls=DjangoJSONEncoder)
        context['supplier_json'] = json.dumps(processed_supplier_data, cls=DjangoJSONEncoder)
        context['porcentagem_custo_operacional'] = round(porcentagem_custo_operacional, 2)
        
        return context

    def form_valid(self, form):
        # Associa o usuário logado à instância de Pricing antes de salvar
        form.instance.user = self.request.user
        

        # Chamada ao método pai para salvar a instância e redirecionar para success_url
        return super().form_valid(form)

    def form_invalid(self, form):
        print("📦 Dados brutos (POST):", self.request.POST)        
        print("❌ Formulário inválido!")        
        # Re-popule o contexto com os dados JSON, assim como em get_context_data
        context = self.get_context_data(form=form) # Passe o formulário com erros para o contexto
        return self.render_to_response(context)
    
class PricingUpdateView(LoginRequiredMixin, UpdateView):
    model = Pricing
    form_class = PricingForm
    template_name = 'pricing_simulation.html'  # reutiliza o mesmo template do CreateView
    success_url = reverse_lazy('list_pricing')

    def get_queryset(self):
        # Garante que o usuário só possa editar suas próprias simulações
        return Pricing.objects.filter(user=self.request.user)
    
    def get_context_data(self, **kwargs):
        # Primeiro, obtenha o contexto padrão da UpdateView
        context = super().get_context_data(**kwargs)
        
        item_class_data = list(ItemClass.objects.filter(active=True).values('id', 'icms_value', 'pis_value', 'cofins_value'))
        supplier_data = list(SupplierProfile.objects.all().values('id', 'tax_value'))

        processed_item_class_data = {
            str(item['id']): {
                'icms_value': float(item['icms_value']),
                'pis_value': float(item['pis_value']),
                'cofins_value': float(item['cofins_value']),
            } for item in item_class_data
        }

        processed_supplier_data = {
            str(supplier['id']): {
                'tax_value': float(supplier['tax_value']),
            } for supplier in supplier_data
        }

        # Calcula a porcentagem de custo operacional também para a edição,
        master = get_object_or_404(CostsMaster, user=self.request.user)
        details = CostsDetail.objects.filter(costs_master=master)        
        total_value = details.aggregate(total=Sum('value'))['total'] or 0
        sales_per_month = master.sales_per_month or 1
        porcentagem_custo_operacional = Decimal(total_value) / Decimal(sales_per_month) * 100
       
        context['item_class_json'] = json.dumps(processed_item_class_data, cls=DjangoJSONEncoder)
        context['supplier_json'] = json.dumps(processed_supplier_data, cls=DjangoJSONEncoder)
        context['porcentagem_custo_operacional'] = round(porcentagem_custo_operacional, 2)

        return context    

    def form_valid(self, form):
        form.instance.user = self.request.user
        return super().form_valid(form)
    
class PricingDeleteView(LoginRequiredMixin, DeleteView):
    model = Pricing
    template_name = 'confirm_delete_pricing.html'
    success_url = reverse_lazy('list_pricing')

    def get_queryset(self):
        # Garante que o usuário só possa excluir suas próprias simulações
        return Pricing.objects.filter(user=self.request.user)
        