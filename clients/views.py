import logging,time
import pandas as pd
import sys
import subprocess  # Importar subprocess para executar o script Python
import os
import re
import uuid
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.core.management import call_command
from django.conf import settings
from django.contrib.auth.models import User, Group
from erp.models import ERP
from .models import Client, Store, Cities, LogIntegration
from .forms import ClientForm, StoreForm
from django.urls import reverse_lazy
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.views import View
from django.views.generic import ListView, CreateView, TemplateView, UpdateView, DeleteView, DetailView
from items.models import Item
from items.forms import CSVUploadForm
from rolepermissions.decorators import has_role_decorator
from rolepermissions.checkers import has_role
from .utils import validateSysmo
from django.db.models import F


@login_required(login_url='login')
@has_role_decorator(['administrador', 'gerente'])
def generate_token(request, client_id):
    print('cliente:', client_id)
    try:
        client = Client.objects.get(id=client_id)
        client.token = uuid.uuid4()  # Gera um novo token UUID
        client.save()
        return JsonResponse({'success': True, 'token': str(client.token)})
    except Client.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Cliente não encontrado'})

class CitySearchView(View):
    def get(self, request, *args, **kwargs):
        term = request.GET.get('q')
        cities = Cities.objects.filter(nome__icontains=term)[:10]
        results = []
        for city in cities:
            results.append({'id': city.pk, 'text': city.nome + ' - ' + city.uf_estado })
        return JsonResponse(results, safe=False)

@method_decorator(login_required(login_url='login'), name='dispatch')
class ClientListView(ListView):
    model = Client
    template_name = 'list_clients.html'
    context_object_name = 'clients'

    def get_queryset(self):
        user = self.request.user
        
        if has_role(user, 'analista'):
            return Client.objects.filter(user_id=user.id)
        else:
            return Client.objects.all()

@method_decorator(login_required(login_url='login'), name='dispatch')
@method_decorator(has_role_decorator(['administrador', 'gerente']), name='dispatch')
class NewClientCreateView(CreateView):
    model = Client
    form_class = ClientForm
    template_name = 'create_client.html'
    success_url = '/clientes/'
    
    def form_invalid(self, form):
        return super().form_invalid(form)    
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['erps'] = ERP.objects.all()
        analysts_group = Group.objects.get(name='analista')
        context['users'] = User.objects.filter(groups=analysts_group)  
        
        return context
    
    def form_valid(self, form):
        cnpj = form.cleaned_data.get('cnpj')
        
        if cnpj:
            # Remove todos os caracteres não numéricos
            numeros = re.sub(r'\D', '', cnpj)
            
            # Aplica a formatação desejada
            if len(numeros) == 14:  # Verifica se há 14 dígitos
                form.instance.cnpj = f"{numeros[:2]}.{numeros[2:5]}.{numeros[5:8]}/{numeros[8:12]}-{numeros[12:]}"
        
        return super().form_valid(form)    
    
@method_decorator(login_required(login_url='login'), name='dispatch')
# @method_decorator(has_role_decorator(['administrador', 'gerente']), name='dispatch')
class ClientUpdateView(UpdateView):
    model = Client
    form_class = ClientForm
    template_name = 'update_client.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['erps'] = ERP.objects.all()
        analysts_group = Group.objects.get(name='analista')
        context['users'] = User.objects.filter(groups=analysts_group)
        # Obtenha o ID do cliente
        client_id = self.kwargs.get('pk')
        context['client_id'] = client_id
        
        # Obtenha a instância do cliente
        client = Client.objects.get(pk=client_id)
        context['client_name'] = client.name  
        context['client_token'] = client.token
        
        # Obtenha as stores associadas ao cliente
        stores = Store.objects.filter(client_id=client_id)
        context['stores'] = stores

        # Adicione o form para adicionar uma nova store
        context['store_form'] = StoreForm() 
        
        # Obtendo o log das integrações para esse cliente
        logs = LogIntegration.objects.filter(client_id=client_id)
        context['logs'] = logs
        return context   
    
    def form_valid(self, form):
        # Obter a instância atual do cliente
        self.object = form.save(commit=False)
        
        # Formatar o CNPJ se preenchido
        cnpj = form.cleaned_data.get('cnpj')
        
        if cnpj:
            # Remove todos os caracteres não numéricos
            numeros = re.sub(r'\D', '', cnpj)
            
            # Aplica a formatação desejada
            if len(numeros) == 14:  # Verifica se há 14 dígitos
                self.object.cnpj = f"{numeros[:2]}.{numeros[2:5]}.{numeros[5:8]}/{numeros[8:12]}-{numeros[12:]}"        
        
        password_route = form.cleaned_data.get('password_route')
        
        if password_route:
            self.object.password_route = password_route
        else:
            # Não salva o campo password_route vazio
            self.object.password_route = self.object.__class__.objects.get(pk=self.object.pk).password_route
        
        self.object.save()
        return super().form_valid(form)       

    def get_success_url(self):
        return reverse_lazy('client_update', kwargs={'pk': self.object.pk})     

@method_decorator(login_required(login_url='login'), name='dispatch')
@method_decorator(has_role_decorator(['administrador', 'gerente']), name='dispatch')
class StoreCreateView(TemplateView):
    template_name = 'update_client.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        client_id = self.kwargs.get('client_id')
        context['client_id'] = client_id
        context['form'] = StoreForm()
        return context

    def post(self, request, *args, **kwargs):
        form = StoreForm(request.POST)
        if form.is_valid():
            client_id = request.POST.get('client')
            form.instance.client = get_object_or_404(Client, pk=client_id)
            store = form.save()
            data = {
                'pk': store.pk,
                'corporate_name': store.corporate_name, 
                'cnpj': store.cnpj,
                'city_name': store.city.nome + ' - ' + store.city.uf_estado,
                'message': "Loja criada com sucesso!"
            }
            return JsonResponse(data)
        else:
            errors = {field: [str(error).replace('Store', 'Loja') for error in errors] for field, errors in form.errors.items()}
            return JsonResponse(errors, status=400)

@method_decorator(login_required(login_url='login'), name='dispatch')
class StoreDetailView(DetailView):
    model = Store
    context_object_name = 'store'

    def get(self, request, *args, **kwargs):
        store = self.get_object()
        data = {
            'id': store.id,
            'corporate_name': store.corporate_name,
            'city_id': store.city.id,
            'city_name': store.city.nome + ' - ' + store.city.uf_estado,
            'cnpj': store.cnpj,
            'connection_route': store.connection_route,
            'is_active': store.is_active,
        }
        return JsonResponse(data)
        
@method_decorator(login_required(login_url='login'), name='dispatch')
@method_decorator(has_role_decorator(['administrador', 'gerente']), name='dispatch')
class StoreUpdateView(UpdateView):
    model = Store
    form_class = StoreForm

    def form_valid(self, form):
        self.object = form.save()
        return JsonResponse({'success': True})

    def form_invalid(self, form):
        return JsonResponse({'success': False, 'errors': form.errors})       
        
@method_decorator(login_required(login_url='login'), name='dispatch')
@method_decorator(has_role_decorator(['administrador', 'gerente']), name='dispatch')
class StoreDeleteView(View):
    def delete(self, request, *args, **kwargs):
        store_id = kwargs.get('pk')
        try:
            store = Store.objects.get(id=store_id)
            store.delete()
            return JsonResponse({'success': True})
        except Store.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Store not found'}, status=404)
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=500)       

class XLSXSimulateValidateItems(View):
    template_name = 'simulate_validate_items.html'

    def get(self, request):
        clients = Client.objects.all()
        context = {
            'clients': clients,
        }
        return render(request, self.template_name, context)

    def post(self, request):
        start_time = time.time()
        form = CSVUploadForm(request.POST, request.FILES)
        if form.is_valid():
            xlsx_file = request.FILES['csv_file']
            client_id = request.POST.get('client') 
            client = get_object_or_404(Client, id=client_id)
            erp_name = client.erp.name  # Pega o nome do ERP associado ao cliente

            try:
                if erp_name != 'SYSMO':
                    error_message = [f"Erro: Base não configurada para esse sistema do cliente escolhido."]
                    self.logger.error(error_message)
                    # return JsonResponse({'error': error_message}, status=400)
                    return JsonResponse({
                        'message': 'Base não configurada.',
                        'errors': error_message,
                        'elapsed_time': elapsed_time
                    }, status=400) 
                else:
                    df = pd.read_excel(xlsx_file, dtype={
                        'tx_codigobarras': str, 
                        'tx_ncm': str, 
                        'tx_cest': str, 
                        'nr_naturezareceita': str,
                        'tx_cbenef': str,  
                    })                    
                    
            except Exception as e:
                # self.logger.error(f"Erro ao ler o arquivo Excel: {e}")
                return JsonResponse({'error': f"Erro ao ler o arquivo Excel: {e}"}, status=400)                    
                
            # Pega todos os itens relacionados a esse cliente
            items_queryset = Item.objects.filter(client=client).values(
                'code', 'barcode', 'description', 'ncm', 'cest', 'cfop', 'icms_cst', 
                'icms_aliquota', 'icms_aliquota_reduzida', 'protege', 'cbenef', 
                'piscofins_cst', 'pis_aliquota', 'cofins_aliquota', 
                naturezareceita_code=F('naturezareceita__code')
            )
            
            # Converte o queryset em uma lista de dicionários
            items_list = list(items_queryset.values())

            # Cria um DataFrame a partir da lista de dicionários
            items_df = pd.DataFrame(items_list)
            
            try:
                # Chama a função de validação
                validation_result = validateSysmo(client_id, items_df, df)
                        
            except Exception as e:  # Catch any unexpected exceptions
                # self.logger.critical(f"Unexpected error: {e}", exc_info=True)  # Log with traceback
                return JsonResponse({'error': 'Erro interno no servidor.'}, status=500)

            end_time = time.time()
            elapsed_time = round(end_time - start_time, 3)
            
            return JsonResponse({
                'message': validation_result['message'],
                'processed_rows': len(df),
                'elapsed_time': elapsed_time
            })

        # self.logger.error(f"Form inválido: {form.errors}")
        return JsonResponse({'errors': form.errors}, status=400)

class RunSelectView(View):
    def get(self, request, client_id):
        client = get_object_or_404(Client, id=client_id)
        try:
            if client.erp.name == 'SYSMO':
                script_execute = 'run_select.py'
            else:
                script_execute = 'run_select_macsistemas.py' 
            # Obter o caminho completo para o script run_select.py
            script_path = os.path.join(settings.BASE_DIR, 'items', 'management', 'commands', script_execute)
            
            # Obter o caminho do interpretador Python atual
            python_executable = sys.executable
            
            # Executar o script como um subprocesso
            # result = subprocess.run(['python', script_path, '--client_id', str(client_id)])
            result = subprocess.run([python_executable, script_path, '--client_id', str(client_id)])

            if result.returncode == 0:  # Código de saída 0 indica sucesso
                return JsonResponse({'status': 'success', 'message': 'Script executed successfully'})
            else:
                return JsonResponse({'status': 'error', 'message': 'Error executing script'})
        except Exception as e:
            print(f"Error: {str(e)}")
            return JsonResponse({'status': 'error', 'message': str(e)})
        
class RunUpdateView(View):
    def get(self, request, client_id):
        client = get_object_or_404(Client, id=client_id)
        try:
            if client.erp.name == 'SYSMO':
                script_execute = 'run_update_sysmo.py'
            else:
                script_execute = 'run_update_macsistemas.py'             
            # Obter o caminho completo para o script run_select.py
            script_path = os.path.join(settings.BASE_DIR, 'items', 'management', 'commands', script_execute)
            
            # Obter o caminho do interpretador Python atual
            python_executable = sys.executable
            
            # Executar o script como um subprocesso
            # result = subprocess.run(['python', script_path, '--client_id', str(client_id)])
            result = subprocess.run([python_executable, script_path, '--client_id', str(client_id)])

            if result.returncode == 0:  # Código de saída 0 indica sucesso
                return JsonResponse({'status': 'success', 'message': 'Dados enviados com sucesso.'})
            else:
                if result.returncode == 2:
                    return JsonResponse({'status': 'warning', 'message': 'Nenhum produto para ser sincronizado.'})
                elif result.returncode == 3:
                    return JsonResponse({'status': 'error', 'message': 'Erro ao executar a atualização.'})
                elif result.returncode == 4:
                    return JsonResponse({'status': 'error', 'message': 'Nao foi possível estabelecer conexão com o cliente.'})
                else:
                    return JsonResponse({'status': 'error', 'message': 'Ocorreu um erro ao executar a sincronização'})
            
        except Exception as e:
            print(f"Error: {str(e)}")
            return JsonResponse({'status': 'error', 'message': str(e)})        
             