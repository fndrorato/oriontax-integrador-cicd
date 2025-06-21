from django.views.generic import ListView, UpdateView, TemplateView
from django.views.generic.edit import CreateView, DeleteView
from django.urls import reverse_lazy
from base.models import States
from shopsim.models import PriceQuote, SupplierProfile
from shopsim.forms import PriceQuoteForm
from django.contrib.auth.mixins import LoginRequiredMixin


class PriceQuoteSimulationListView(LoginRequiredMixin, ListView):
    model = PriceQuote
    template_name = 'list_simulation_shop.html'  # mesmo nome do template criado
    context_object_name = 'simulations'
    ordering = ['-created_at']

    def get_queryset(self):
        return PriceQuote.objects.filter(user=self.request.user) 

class PriceQuoteCreateView(LoginRequiredMixin, CreateView):
    model = PriceQuote
    form_class = PriceQuoteForm
    template_name = 'shop_simulation.html'
    success_url = reverse_lazy('simulation_shop_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Cria um dicionário com os dados já formatados
        context['supplier_tax_json'] = {
            str(s.id): float(f"{s.tax_value:.2f}".replace(',', '.'))
            for s in SupplierProfile.objects.all()
        }
        
        context['state_tax_json'] = {
            str(st.id): {
                'code': st.code,
                'aliquota': float(f"{st.aliquota_inter:.2f}".replace(',', '.'))
            }
            for st in States.objects.all()
        }

        return context
    
    def form_valid(self, form):
        print("📦 Dados brutos (POST):", self.request.POST)
        print("✅ Dados limpos (cleaned_data):", form.cleaned_data)             
        # Atribui o usuário logado à instância
        form.instance.user = self.request.user
        
        # --- LÓGICA PARA TRATAR best_option ---
        # best_option_input_value virá do campo hidden, pode ser o ID do estado ou 'Empate'
        best_option_input_value = form.cleaned_data.get('best_option')
        
        best_option_instance = None # Inicializa como None
        
        # Se o valor não for vazio e não for 'Empate'
        if best_option_input_value and best_option_input_value != 'Empate':
            try:
                # Tenta converter o valor para inteiro, pois esperamos um ID
                state_id = int(best_option_input_value)
                # Busca a instância do States pelo ID
                best_option_instance = States.objects.get(id=state_id)
            except (ValueError, States.DoesNotExist):
                # Lida com casos onde o valor não é um inteiro válido ou o estado não existe
                print(f"ID de estado inválido ou inexistente para best_option: '{best_option_input_value}'")
                best_option_instance = None # Garante que seja None se houver erro
        
        # Atribui a instância do Estado (ou None) ao campo best_option do modelo
        # Se best_option_input_value for 'Empate' ou vazio, best_option_instance já será None
        form.instance.best_option = best_option_instance

        # Salva a instância do modelo
        return super().form_valid(form) 
    
    def form_invalid(self, form):
        print("📦 Dados brutos (POST):", self.request.POST)        
        print("❌ Formulário inválido!")
        print(form.errors)  # Mostra os erros que impedem a validação
        return super().form_invalid(form)         


class PriceQuoteSimulationUpdateView(LoginRequiredMixin, UpdateView):
    model = PriceQuote
    form_class = PriceQuoteForm
    template_name = 'shop_simulation.html'  # reutiliza o mesmo template do CreateView
    success_url = reverse_lazy('simulation_shop_list')

    def get_queryset(self):
        # Garante que o usuário só possa editar suas próprias simulações
        return PriceQuote.objects.filter(user=self.request.user)

    def form_valid(self, form):
        form.instance.user = self.request.user
        return super().form_valid(form)
    
class PriceQuoteSimulationDeleteView(LoginRequiredMixin, DeleteView):
    model = PriceQuote
    template_name = 'confirm_delete_simulation.html'
    success_url = reverse_lazy('simulation_shop_list')

    def get_queryset(self):
        # Garante que o usuário só possa excluir suas próprias simulações
        return PriceQuote.objects.filter(user=self.request.user)
    
