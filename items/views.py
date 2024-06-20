import csv
import io
import os
import time
import json
import logging
import pandas as pd
from django.conf import settings
from django.shortcuts import render, get_object_or_404, redirect
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.http import JsonResponse, FileResponse, HttpResponseNotFound, HttpResponse
from django.utils import timezone
from django.core.exceptions import ValidationError, ObjectDoesNotExist
from django.contrib import messages
from django.urls import reverse_lazy
from django.db import transaction, connection
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.db.utils import DataError
from django.views import View
from django.views.generic import ListView, CreateView, UpdateView, DeleteView, DetailView
from django.contrib.auth.models import User
from clients.models import Client
from .models import Item
from .forms import ItemForm, CSVUploadForm
from impostos.models import IcmsCst, IcmsAliquota, IcmsAliquotaReduzida, Protege, CBENEF, PisCofinsCst, NaturezaReceita, Cfop
from django.http import JsonResponse
from django.views.decorators.http import require_GET, require_POST
from .models import Item
import openpyxl
from openpyxl import load_workbook
from openpyxl.utils import get_column_letter
from auditlog.models import LogEntry
from app.utils import get_auditlog_history


ACTION_MAPPING = {
    LogEntry.Action.CREATE: 'Criação',
    LogEntry.Action.UPDATE: 'Atualização',
    LogEntry.Action.DELETE: 'Exclusão'
}

def get_item_logs(request, model_name, object_id):
    logs = get_auditlog_history(model_name, object_id)
    logs_data = []

    for log in logs:
        changes = log.changes

        if log.action == LogEntry.Action.CREATE:
            # Filtro para excluir valores 'old' que são None e os campos indesejados
            filtered_changes = {
                k: [v for v in values if v != "None"]
                for k, values in changes.items()
                if k not in ['user_updated', 'user_created', 'is_pending_sync', 'id']
            }

            # Substituição do ID de naturezareceita pelo código
            if 'naturezareceita' in filtered_changes:
                natureza_id = filtered_changes['naturezareceita'][0]
                try:
                    natureza = NaturezaReceita.objects.get(id=natureza_id)
                    filtered_changes['naturezareceita'] = [natureza.code]  # Substitui o ID pelo código
                except NaturezaReceita.DoesNotExist:
                    pass  # Mantém o ID se a natureza não for encontrada
        else:
            filtered_changes = changes

        log_entry = {
            'action': ACTION_MAPPING.get(log.action, log.get_action_display()),
            'actor': log.actor.get_full_name() if log.actor else 'Unknown',
            'timestamp': log.timestamp.strftime('%d/%m/%Y %H:%M'),
            'changes': filtered_changes,
        }
        logs_data.append(log_entry)

    return JsonResponse({'logs': logs_data})

def export_items_to_excel(request, client_id):
    # Obter o cliente
    client = Client.objects.get(id=client_id)
    # Obter todos os itens do cliente
    items = Item.objects.filter(client=client)

    # Criar um Workbook e uma planilha
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = 'Items'

    # Escrever os cabeçalhos
    headers = ['Cliente', 'codigo', 'barcode', 'description', 'ncm', 'cest', 'cfop', 'icms_cst', 'icms_aliquota',
               'icms_aliquota_reduzida', 'protege', 'cbenef', 'piscofins_cst', 'pis_aliquota', 'cofins_aliquota',
               'naturezareceita']
    for col_num, header in enumerate(headers, 1):
        col_letter = get_column_letter(col_num)
        ws[f'{col_letter}1'] = header

    # Escrever os dados dos itens
    for row_num, item in enumerate(items, 2):
        ws[f'A{row_num}'] = item.id
        ws[f'A{row_num}'] = item.client.name  # Assumindo que Client tem um campo `name`
        ws[f'B{row_num}'] = item.code
        ws[f'C{row_num}'] = item.barcode
        ws[f'D{row_num}'] = item.description
        ws[f'E{row_num}'] = item.ncm
        ws[f'F{row_num}'] = item.cest        
        ws[f'G{row_num}'] = item.cfop.cfop  # Assumindo que CFOP tem um campo `code`
        ws[f'H{row_num}'] = item.icms_cst.code  # Assumindo que ICMS CST tem um campo `code`
        ws[f'I{row_num}'] = item.icms_aliquota.code  # Assumindo que ICMS Aliquota tem um campo `code`
        ws[f'J{row_num}'] = item.icms_aliquota_reduzida
        ws[f'K{row_num}'] = item.protege.code if item.protege else ''  # Assumindo que Protege tem um campo `code`
        ws[f'L{row_num}'] = item.cbenef.code if item.cbenef else ''  # Assumindo que CBenef tem um campo `code`
        ws[f'M{row_num}'] = item.piscofins_cst.code  # Assumindo que PIS Cofins CST tem um campo `code`
        ws[f'N{row_num}'] = item.pis_aliquota
        ws[f'O{row_num}'] = item.cofins_aliquota
        ws[f'P{row_num}'] = item.naturezareceita.code if item.naturezareceita else ''  # Assumindo que Natureza Receita tem um campo `code`

    # Salvar o arquivo em uma resposta HTTP
    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = f'attachment; filename=items_{client.name}.xlsx'
    wb.save(response)

    return response

def download_file(request, filename):
    file_path = os.path.join(settings.STATICFILES_DIRS[0], 'downloads', filename)
    if os.path.exists(file_path):
        response = FileResponse(open(file_path, 'rb'))
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response
    else:
        return HttpResponseNotFound('Arquivo não encontrado')

def validate_item(request):
    code = request.GET.get('code')
    client = request.GET.get('client')

    if not code or not client:
        return JsonResponse({'success': False, 'message': 'Code and client are required.'})

    exists = Item.objects.filter(code=code, client=client).exists()
    if exists:
        return JsonResponse({'success': False, 'message': 'This code for this client already exists.'})
    
    return JsonResponse({'success': True, 'message': 'This code for this client is available.'})

@method_decorator(login_required(login_url='login'), name='dispatch')
class ItemListView(ListView):
    model = Item
    template_name = 'list_item.html'
    context_object_name = 'items'
    paginate_by = 20  # Defina quantos itens você quer por página

    def get_queryset(self):
        client_id = self.kwargs.get('client_id')
        client = get_object_or_404(Client, id=client_id)

        queryset = Item.objects.filter(client=client).order_by('description')
        # Filter with ForeignKey lookups and other fields
        filter_kwargs = {}
        for field_name in ['code', 'barcode', 'description', 'ncm', 'cest', 'icms_aliquota_reduzida', 'pis_aliquota', 'cofins_aliquota']:
            value = self.request.GET.get(field_name)
            if value:
                filter_kwargs[f"{field_name}__icontains"] = value

        queryset = queryset.filter(**filter_kwargs)

        # Handle ForeignKey filters separately
        for field_name in ['cfop', 'icms_cst', 'icms_aliquota', 'protege', 'cbenef', 'piscofins_cst', 'naturezareceita']:
            value = self.request.GET.get(field_name)
            if value:
                try:
                    if field_name == 'naturezareceita':
                        queryset = queryset.filter(**{f"{field_name}__code__icontains": value})
                    else:
                        queryset = queryset.filter(**{f"{field_name}_id": int(value)})
                except ValueError:
                    pass  # Skip filter if value is not a valid integer

        return queryset
   

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        client = get_object_or_404(Client, id=self.kwargs.get('client_id'))
        context['client'] = client
        context['client_name'] = client.name
        context['client_id'] = client.id
        context['filter_params'] = self.request.GET
        # Adiciona os cálculos de paginação
        paginator = context['paginator']
        page_obj = context['page_obj']
        total_pages = paginator.num_pages
        current_page = page_obj.number

        if total_pages <= 10:
            page_range = range(1, total_pages + 1)
        else:
            if current_page <= 4:
                page_range = list(range(1, 6)) + ['...'] + [total_pages - 1, total_pages]
            elif current_page > total_pages - 4:
                page_range = [1, 2, '...'] + list(range(total_pages - 4, total_pages + 1))
            else:
                page_range = [1, 2, '...'] + list(range(current_page - 2, current_page + 3)) + ['...'] + [total_pages - 1, total_pages]

        context['page_range'] = page_range
        return context

@method_decorator(login_required(login_url='login'), name='dispatch')    
class ItemDetailView(DetailView):
    model = Item
    template_name = 'item_detail.html'
    context_object_name = 'item'

@method_decorator(login_required(login_url='login'), name='dispatch')
class ItemCreateView(CreateView):
    model = Item
    form_class = ItemForm
    template_name = 'create_item.html'
    
    def get_success_url(self):
        client_id = self.kwargs['client_id']
        return reverse_lazy('item_list', kwargs={'client_id': client_id})    
      
    def get_queryset(self):
        client_id = self.kwargs.get('client_id')
        client = get_object_or_404(Client, id=client_id)
        return Item.objects.filter(client=client)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        client = get_object_or_404(Client, id=self.kwargs.get('client_id'))
        context['client'] = client
        context['client_name'] = client.name 
        context['client_id'] = client.id 
        # Obtém todas as opções de icms_aliquota_reduzida
        icms_aliquota_reduzida_choices = [
            (str(ia.code), str(ia.code)) for ia in IcmsAliquotaReduzida.objects.all()
        ]
        context['icms_aliquota_reduzida_choices'] = icms_aliquota_reduzida_choices        
        return context   
    
    def form_invalid(self, form):
        # Exibir erros do formulário
        for field, errors in form.errors.items():
            for error in errors:
                print(f"Erro no campo {field}: {error}")        
        messages.error(self.request, 'Erro ao salvar o item. Verifique os dados fornecidos.')
        return super().form_invalid(form)  
    
    def form_valid(self, form):
        # Registrar o usuário que fez a atualização
        item = form.save(commit=False)
        item.user_created = self.request.user
        item.user_updated = self.request.user
        item.save()
        return super().form_valid(form)            

class ItemUpdateView(UpdateView):
    model = Item
    form_class = ItemForm
    template_name = 'update_item.html'

    def get_queryset(self):
        client_id = self.kwargs.get('client_id')
        client = get_object_or_404(Client, id=client_id)
        return Item.objects.filter(client=client)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        client = get_object_or_404(Client, id=self.kwargs.get('client_id'))
        context['client'] = client
        context['client_name'] = client.name 
        context['client_id'] = client.id 
        context['user_updated'] = self.object.user_updated
        context['updated_at'] = self.object.updated_at
        # Obtém todas as opções de icms_aliquota_reduzida
        icms_aliquota_reduzida_choices = [
            (str(ia.code), str(ia.code)) for ia in IcmsAliquotaReduzida.objects.all()
        ]
        context['icms_aliquota_reduzida_choices'] = icms_aliquota_reduzida_choices          
        return context 
    
    def form_invalid(self, form):
        # Exibir erros do formulário
        for field, errors in form.errors.items():
            for error in errors:
                print(f"Erro no campo {field}: {error}")        
        messages.error(self.request, 'Erro ao salvar o item. Verifique os dados fornecidos.')
        return super().form_invalid(form)     
    
    def form_valid(self, form):
        # Registrar o usuário que fez a atualização
        item = form.save(commit=False)
        item.user_updated = self.request.user
        item.save()
        return super().form_valid(form)    
    
    def get_success_url(self):
        return reverse_lazy('item_list', kwargs={'client_id': self.object.client_id})          

class ItemDeleteView(DeleteView):
    model = Item
    template_name = 'item_confirm_delete.html'
    success_url = reverse_lazy('item_list')    

class XLSXUploadView(View):
    template_name = 'upload_items.html'

    def get(self, request, client_id):
        client = get_object_or_404(Client, id=client_id)
        form = CSVUploadForm()
        context = {
            'form': form,
            'client': client,
        }
        return render(request, self.template_name, context)

    def post(self, request, client_id):
        client = get_object_or_404(Client, id=client_id)
        form = CSVUploadForm(request.POST, request.FILES)
        if form.is_valid():
            xlsx_file = request.FILES['csv_file']
            wb = load_workbook(filename=xlsx_file)
            sheet = wb.active

            errors = []
            items = []

            user = request.user
            current_time = timezone.now()

            row_number = 2  # Começa com 2 para pular o cabeçalho

            for row in sheet.iter_rows(min_row=2, values_only=True):  # Pulando a primeira linha (cabeçalho)
                try:
                    # print(f"Processando linha: {row}")
                    piscofins_cst_code = str(row[11])
                    if len(piscofins_cst_code) == 1:
                        piscofins_cst_code = f"0{piscofins_cst_code}"
                    piscofins_cst_code = str(piscofins_cst_code)                    
                    # print(f"PisCofinsCst: {piscofins_cst_code}")
                    

                    
                    # Construir o dicionário para passar ao formulário
                    item_data = {
                        'client': client.id,
                        'code': row[0],
                        'barcode': row[1],
                        'description': row[2],
                        'ncm': row[3],
                        'cest': row[4],
                        'cfop': Cfop.objects.get(cfop=row[5]).cfop,
                        'icms_cst': IcmsCst.objects.get(code=row[6]).code,
                        'icms_aliquota': IcmsAliquota.objects.get(code=row[7]).code,
                        'icms_aliquota_reduzida': IcmsAliquota.objects.get(code=row[8]).code,
                        'protege': row[9],
                        'cbenef': row[10],
                        'piscofins_cst': PisCofinsCst.objects.get(code=piscofins_cst_code),
                        'pis_aliquota': PisCofinsCst.objects.get(code=piscofins_cst_code).pis_aliquota,
                        'cofins_aliquota': PisCofinsCst.objects.get(code=piscofins_cst_code).cofins_aliquota,
                        'naturezareceita': NaturezaReceita.objects.get(code=row[14]).id if row[14] else None,
                        'is_active': True,
                        'is_pending_sync': True,
                        'updated_at': current_time,
                        'user_updated': user.id,
                    }
                    # print(item_data)
                    try:
                        item = Item.objects.get(client=client, code=row[0])
                        # Atualiza os campos do item existente
                        item_form = ItemForm(instance=item, data=item_data)
                    except Item.DoesNotExist:
                        # Cria um novo item se ele não existir
                        item_form = ItemForm(data=item_data)

                    # Usar o formulário para validar o item
                    if item_form.is_valid():
                        item = item_form.save(commit=False)
                        item.user_updated = user
                        items.append(item)
                    else:
                        error_messages = []
                        for field_errors in item_form.errors.values():
                            for error in field_errors:
                                error_messages.append(str(error))
                        errors.append(f"Erro na linha {row_number}: {', '.join(error_messages)}")


                except (Cfop.DoesNotExist, IcmsCst.DoesNotExist, IcmsAliquota.DoesNotExist,
                        IcmsAliquotaReduzida.DoesNotExist, Protege.DoesNotExist, CBENEF.DoesNotExist,
                        PisCofinsCst.DoesNotExist, NaturezaReceita.DoesNotExist) as e:
                    errors.append(f"Erro na linha {row_number}: {str(e)}")

                row_number += 1  # Incrementa o contador de linha

            if errors:
                return JsonResponse({'errors': errors}, status=400)
            else:
                # Salvar todos os itens
                for item in items:
                    item.save()
                return JsonResponse({'message': 'Todos os itens foram salvos/atualizados com sucesso!'})

        print(f"Form inválido: {form.errors}")
        return JsonResponse({'errors': form.errors}, status=400)

  
# class XLSXUploadViewV2(View):
#     template_name = 'upload_items.html'

#     def get(self, request, client_id):
#         client = get_object_or_404(Client, id=client_id)
#         form = CSVUploadForm()
#         context = {
#             'form': form,
#             'client': client,
#         }
#         return render(request, self.template_name, context)

#     logger = logging.getLogger(__name__)  # Configurar o logger

#     # @transaction.atomic  # Garante a atomicidade da transação
#     def post(self, request, client_id):
#         start_time = time.time()
#         client = get_object_or_404(Client, id=client_id)
#         form = CSVUploadForm(request.POST, request.FILES)
#         if form.is_valid():
#             xlsx_file = request.FILES['csv_file']
#             df = pd.read_excel(xlsx_file)
            
#             # Pré-validar códigos
#             valid_cfops = set(Cfop.objects.values_list('cfop', flat=True))
#             valid_icms_csts = set(IcmsCst.objects.values_list('code', flat=True))
#             valid_icms_aliquotas = set(IcmsAliquota.objects.values_list('code', flat=True))
#             valid_piscofins_csts = set(PisCofinsCst.objects.values_list('code', flat=True))
#             valid_natureza_receitas = set(NaturezaReceita.objects.values_list('code', flat=True))
#             valid_proteges = set(Protege.objects.values_list('code', flat=True))
#             valid_cbenefs = set(CBENEF.objects.values_list('code', flat=True))
            
#             # Adicionar a possibilidade de ser vazio/em branco
#             valid_natureza_receitas.add(None)
#             valid_cbenefs.add(None)
            
#             # Carregar os dados de PisCofinsCst e NaturezaReceita em DataFrames
#             piscofins_cst_df = pd.DataFrame(list(PisCofinsCst.objects.values('code', 'pis_aliquota', 'cofins_aliquota')))
#             natureza_receita_df = pd.DataFrame(list(NaturezaReceita.objects.values('code', 'id', 'piscofins_cst_id')))

#             # Converter os DataFrames para dicionários para consulta eficiente
#             pis_cofins_cst_dict = piscofins_cst_df.set_index('code').to_dict('index')
#             natureza_receita_dict = natureza_receita_df.set_index(['code', 'piscofins_cst_id']).to_dict('index')
            
#             # Função para buscar IDs a partir dos códigos
#             def get_natureza_receita_id(code, piscofins_cst_code):
#                 return natureza_receita_dict.get((code, piscofins_cst_code), {}).get('id')            

#             # Convertendo os dados para strings e preenchendo zeros à esquerda quando necessário
#             df['barcode'] = df['barcode'].fillna(0).astype(int).astype(str)
#             df['ncm'] = df['ncm'].astype(str)
#             df['cest'] = df['cest'].fillna(0).astype(int).astype(str)
#             df['cfop'] = df['cfop'].astype(int)
#             df['icms_cst'] = df['icms_cst'].astype(str)
#             df['icms_aliquota'] = df['icms_aliquota'].astype(int)
#             df['icms_aliquota_reduzida'] = df['icms_aliquota_reduzida'].astype(int)
#             df['piscofins_cst'] = df['piscofins_cst'].astype(str).str.zfill(2)
#             # df['naturezareceita'] = df['naturezareceita'].astype(str).replace('0', None)
#             df['naturezareceita'] = df['naturezareceita'].fillna('').astype(str).str.zfill(3).replace(['000', 'nan'], None)
#             df['protege'] = df['protege'].astype(int)
#             df['cbenef'] = df['cbenef'].astype(str).replace('nan', None)
#             # Truncar campos que excedem o tamanho máximo permitido
#             df['description'] = df['description'].str[:255]
#             df['cbenef'] = df['cbenef'].str[:8]
            

#             # Lista para armazenar as linhas inválidas e seus motivos
#             invalid_details = []

#             # Função para verificar linhas inválidas
#             def check_invalid_rows(df, column_name, valid_set):
#                 # Filtrar as linhas inválidas da coluna especificada, considerando valores não nulos e valores nulos
#                 invalid_rows = df[(~df[column_name].isin(valid_set)) & (~df[column_name].isnull())]
                
#                 for index, row in invalid_rows.iterrows():
#                     error_message = f"Erro na linha[{column_name}] {index + 2}: {row[column_name]} é um valor inválido."
#                     invalid_details.append(error_message)  # Adicionar o erro à lista                    
#                 return invalid_rows

#             # Verificar cada coluna separadamente e parar se encontrar alguma linha inválida
#             columns_to_check = [
#                 ('cfop', valid_cfops),
#                 ('icms_cst', valid_icms_csts),
#                 ('icms_aliquota', valid_icms_aliquotas),
#                 ('icms_aliquota_reduzida', valid_icms_aliquotas),
#                 ('piscofins_cst', valid_piscofins_csts),
#                 ('naturezareceita', valid_natureza_receitas),
#                 ('protege', valid_proteges),
#                 ('cbenef', valid_cbenefs)
#             ]

#             for column_name, valid_set in columns_to_check:
#                 invalid_rows = check_invalid_rows(df, column_name, valid_set)
#                 if not invalid_rows.empty:
#                     break  # Interrompe o processo ao encontrar linhas inválidas

#             if invalid_details:
#                 end_time = time.time()
#                 elapsed_time = round(end_time - start_time, 3)                 
#                 return JsonResponse({
#                     'message': 'Linhas inválidas encontradas.',
#                     'errors': invalid_details,
#                     'elapsed_time': elapsed_time
#                 }, status=400)

#             codigos = df['codigo'].tolist()  
#             # Pré-carregar os itens existentes no banco de dados
#             existing_items = {item.code: item for item in Item.objects.filter(client=client, code__in=df['codigo'])}

            
#             # Busque todas as instâncias de PisCofinsCst de uma vez para eficiência
#             pis_cofins_cst_instances = {obj.code: obj for obj in PisCofinsCst.objects.filter(code__in=df['piscofins_cst'])}
            
#             items_to_create = []
#             items_to_update = []
#             user = request.user
#             current_time = timezone.now()
#             errors = []  # Lista para armazenar os erros
                                     
#             #### ORIGINAL #####  
#             batch_size = 10000  # Define o tamanho do lote
            
#             with transaction.atomic():  # Transação atômica              
#                 for index, row in df.iterrows():
#                     try:
#                         piscofins_cst_code = row['piscofins_cst']  # Garante que o código tenha 2 dígitos

#                         # Obtenha a instância de PisCofinsCst correspondente
#                         piscofins_cst = pis_cofins_cst_instances.get(piscofins_cst_code)
#                         if not piscofins_cst:
#                             raise ObjectDoesNotExist(f"PisCofinsCst com código {piscofins_cst_code} não encontrado")

#                         pis_aliquota = piscofins_cst.pis_aliquota
#                         cofins_aliquota = piscofins_cst.cofins_aliquota
                        
#                         # Buscar o id de NaturezaReceita no DataFrame carregado
#                         natureza_receita_id = get_natureza_receita_id(row['naturezareceita'], piscofins_cst_code)
#                         if not natureza_receita_id and row['naturezareceita'] != None:
#                             raise ValueError(f"NaturezaReceita com código {row['naturezareceita']} e PisCofinsCst {piscofins_cst_code} não encontrado")

#                         item_data = {
#                             'client': client,
#                             'code': row['codigo'],
#                             'barcode': row['barcode'],
#                             'description': row['description'],
#                             'ncm': row['ncm'],
#                             'cest': row['cest'],
#                             'cfop_id': row['cfop'],  # Verifique se o valor de 'cfop' é um número dentro do limite de 7 caracteres
#                             'icms_cst_id': row['icms_cst'],
#                             'icms_aliquota_id': row['icms_aliquota'],
#                             'icms_aliquota_reduzida': row['icms_aliquota_reduzida'],
#                             'protege_id': row['protege'],
#                             'cbenef_id': row['cbenef'] if row['cbenef'] in valid_cbenefs else None,  # Verifique se o valor de 'cbenef' está dentro do limite de 8 caracteres
#                             'piscofins_cst': piscofins_cst,
#                             'pis_aliquota': pis_aliquota,
#                             'cofins_aliquota': cofins_aliquota,
#                             'naturezareceita_id': natureza_receita_id,
#                             'is_active': True,
#                             'is_pending_sync': True,
#                             'updated_at': current_time,
#                             'user_updated': user,
#                         }

#                         # Verificar se o item existe
#                         if row['codigo'] in existing_items:
#                             # Atualizar item existente
#                             item = existing_items[row['codigo']]
#                             for key, value in item_data.items():
#                                 setattr(item, key, value)
#                             items_to_update.append(item)
#                         else:
#                             # Criar novo item
#                             new_item = Item(**item_data)
#                             items_to_create.append(new_item)

#                     except (ObjectDoesNotExist, ValidationError, TypeError, ValueError) as e:
#                         error_message = f"Erro na linha {index + 2}: {e}"
#                         self.logger.error(error_message)  # Log do erro para o servidor
#                         errors.append(error_message)  # Adicionar o erro à lista
                        
#                 # Verificar se houve erros antes de prosseguir
#                 if errors:
#                     end_time = time.time()
#                     elapsed_time = round(end_time - start_time, 3)                
#                     return JsonResponse({
#                         'message': 'Erros encontrados durante o processamento do arquivo.',
#                         'errors': errors,
#                         'elapsed_time': elapsed_time
#                     }, status=400)

#                 # Bulk create e bulk update em lotes
#                 for i in range(0, len(items_to_create), batch_size):
#                     batch = items_to_create[i:i + batch_size]
#                     Item.objects.bulk_create(batch, ignore_conflicts=True)
#                     # connection.commit()  # Confirma a transação após cada lote

#                 if items_to_update:
#                     for i in range(0, len(items_to_update), batch_size):
#                         batch = items_to_update[i:i + batch_size]
#                         Item.objects.bulk_update(batch, fields=[...])
#                         # connection.commit()  # Confirma a transação após cada lote
                        
#                 # Bulk create e bulk update
#                 # Item.objects.bulk_create(items_to_create, ignore_conflicts=True)
#                 # if items_to_update:
#                 #     Item.objects.bulk_update(items_to_update, fields=[
#                 #         'barcode', 'description', 'ncm', 'cest', 'cfop', 'icms_cst', 
#                 #         'icms_aliquota', 'icms_aliquota_reduzida', 'protege', 'cbenef', 
#                 #         'piscofins_cst', 'pis_aliquota', 'cofins_aliquota', 'naturezareceita', 
#                 #         'is_active', 'is_pending_sync', 'updated_at', 'user_updated'
#                 #     ])

#             end_time = time.time()
#             elapsed_time = round(end_time - start_time, 3)

#             return JsonResponse({
#                 'message': 'Todos os itens foram salvos/atualizados com sucesso!',
#                 'processed_rows': len(df),
#                 'elapsed_time': elapsed_time
#             })

#         print(f"Form inválido: {form.errors}")
#         return JsonResponse({'errors': form.errors}, status=400)
class XLSXUploadViewV2(View):
    template_name = 'upload_items.html'
    logger = logging.getLogger(__name__)  # Configurar o logger

    def get(self, request, client_id):
        client = get_object_or_404(Client, id=client_id)
        form = CSVUploadForm()
        context = {
            'form': form,
            'client': client,
        }
        return render(request, self.template_name, context)

    def post(self, request, client_id):
        start_time = time.time()
        client = get_object_or_404(Client, id=client_id)
        form = CSVUploadForm(request.POST, request.FILES)
        if form.is_valid():
            xlsx_file = request.FILES['csv_file']
            try:
                df = pd.read_excel(xlsx_file, dtype={'ncm': str, 'cest': str, 'barcode': str, 'naturezareceita': str})
            except Exception as e:
                self.logger.error(f"Erro ao ler o arquivo Excel: {e}")
                return JsonResponse({'error': f"Erro ao ler o arquivo Excel: {e}"}, status=400)
            
            try:
                valid_cfops = set(Cfop.objects.values_list('cfop', flat=True))
                valid_icms_csts = set(IcmsCst.objects.values_list('code', flat=True))
                valid_icms_aliquotas = set(IcmsAliquota.objects.values_list('code', flat=True))
                valid_piscofins_csts = set(PisCofinsCst.objects.values_list('code', flat=True))
                valid_natureza_receitas = set(NaturezaReceita.objects.values_list('code', flat=True))
                valid_proteges = set(Protege.objects.values_list('code', flat=True))
                valid_cbenefs = set(CBENEF.objects.values_list('code', flat=True))
                
                valid_natureza_receitas.add(None)
                valid_cbenefs.add(None)

                piscofins_cst_df = pd.DataFrame(list(PisCofinsCst.objects.values('code', 'pis_aliquota', 'cofins_aliquota')))
                natureza_receita_df = pd.DataFrame(list(NaturezaReceita.objects.values('code', 'id', 'piscofins_cst_id')))
                
                pis_cofins_cst_dict = piscofins_cst_df.set_index('code').to_dict('index')
                natureza_receita_dict = natureza_receita_df.set_index(['code', 'piscofins_cst_id']).to_dict('index')
                
                def get_natureza_receita_id(code, piscofins_cst_code):
                    return natureza_receita_dict.get((code, piscofins_cst_code), {}).get('id')            

                # df['barcode'] = df['barcode'].fillna(0).astype(int).astype(str)
                df['barcode'] = df['barcode'].fillna('').astype(str)
                df['ncm'] = df['ncm'].astype(str)
                # df['cest'] = df['cest'].fillna(0).astype(int).astype(str)
                df['cest'] = df['cest'].fillna('').astype(str)
                df['cfop'] = df['cfop'].astype(int)
                df['icms_cst'] = df['icms_cst'].astype(str)
                df['icms_aliquota'] = df['icms_aliquota'].astype(int)
                df['icms_aliquota_reduzida'] = df['icms_aliquota_reduzida'].astype(int)
                df['piscofins_cst'] = df['piscofins_cst'].astype(str).str.zfill(2)
                df['naturezareceita'] = df['naturezareceita'].fillna('').astype(str).str.zfill(3).replace(['000', 'nan'], None)
                df['protege'] = df['protege'].astype(int)
                df['cbenef'] = df['cbenef'].astype(str).replace('nan', None)
                df['description'] = df['description'].str[:255]
                df['cbenef'] = df['cbenef'].str[:8]

                invalid_details = []

                def check_invalid_rows(df, column_name, valid_set=None, length=None, allow_empty=False):
                    if length is not None:
                        if allow_empty:
                            invalid_rows = df[(df[column_name].apply(lambda x: len(x) != length and x != ''))]
                        else:
                            invalid_rows = df[df[column_name].apply(lambda x: len(x) != length)]
                        for index, row in invalid_rows.iterrows():
                            error_message = f"Erro na linha {index + 2} [{column_name}]: {row[column_name]} não tem {length} dígitos."
                            invalid_details.append(error_message)
                    elif valid_set is not None:
                        invalid_rows = df[(~df[column_name].isin(valid_set)) & (~df[column_name].isnull())]
                        for index, row in invalid_rows.iterrows():
                            error_message = f"Erro na linha {index + 2} [{column_name}]: {row[column_name]} é um valor inválido."
                            invalid_details.append(error_message)
                    else:
                        invalid_rows = pd.DataFrame()
                    return invalid_rows

                
                # def check_invalid_rows(df, column_name, valid_set):
                #     invalid_rows = df[(~df[column_name].isin(valid_set)) & (~df[column_name].isnull())]
                #     for index, row in invalid_rows.iterrows():
                #         error_message = f"Erro na linha[{column_name}] {index + 2}: {row[column_name]} é um valor inválido."
                #         invalid_details.append(error_message)
                #     return invalid_rows

                columns_to_check = [
                    ('cfop', valid_cfops),
                    ('icms_cst', valid_icms_csts),
                    ('icms_aliquota', valid_icms_aliquotas),
                    ('icms_aliquota_reduzida', valid_icms_aliquotas),
                    ('piscofins_cst', valid_piscofins_csts),
                    ('naturezareceita', valid_natureza_receitas),
                    ('protege', valid_proteges),
                    ('cbenef', valid_cbenefs),
                    ('ncm', None, 8),
                    ('cest', None, 7, True)  # Verificar comprimento de 7 dígitos, permitir vazio
                ]

                for column_name, valid_set, *length in columns_to_check:
                    if len(length) == 2:  # Se fornecidos length e allow_empty
                        invalid_rows = check_invalid_rows(df, column_name, valid_set, length[0], length[1])
                    elif length:  # Se fornecido apenas length
                        invalid_rows = check_invalid_rows(df, column_name, valid_set, length[0])
                    else:  # Se não fornecido length
                        invalid_rows = check_invalid_rows(df, column_name, valid_set)
                    
                    if not invalid_rows.empty:
                        break

                if invalid_details:
                    end_time = time.time()
                    elapsed_time = round(end_time - start_time, 3)
                    return JsonResponse({
                        'message': 'Linhas inválidas encontradas.',
                        'errors': invalid_details,
                        'elapsed_time': elapsed_time
                    }, status=400)

                codigos = df['codigo'].tolist()  
                existing_items = {item.code: item for item in Item.objects.filter(client=client, code__in=df['codigo'])}
                pis_cofins_cst_instances = {obj.code: obj for obj in PisCofinsCst.objects.filter(code__in=df['piscofins_cst'])}
                
                items_to_create = []
                items_to_update = []
                user = request.user
                current_time = timezone.now()
                errors = []

                batch_size = 10000

                with transaction.atomic():                
                    for index, row in df.iterrows():
                        try:
                            piscofins_cst_code = row['piscofins_cst']
                            piscofins_cst = pis_cofins_cst_instances.get(piscofins_cst_code)
                            if not piscofins_cst:
                                raise ObjectDoesNotExist(f"PisCofinsCst com código {piscofins_cst_code} não encontrado")

                            pis_aliquota = piscofins_cst.pis_aliquota
                            cofins_aliquota = piscofins_cst.cofins_aliquota
                            
                            natureza_receita_id = get_natureza_receita_id(row['naturezareceita'], piscofins_cst_code)
                            if not natureza_receita_id and row['naturezareceita'] != None:
                                raise ValueError(f"NaturezaReceita com código {row['naturezareceita']} e PisCofinsCst {piscofins_cst_code} não encontrado")

                            item_data = {
                                'client': client,
                                'code': row['codigo'],
                                'barcode': row['barcode'],
                                'description': row['description'],
                                'ncm': row['ncm'],
                                'cest': row['cest'],
                                'cfop_id': row['cfop'],
                                'icms_cst_id': row['icms_cst'],
                                'icms_aliquota_id': row['icms_aliquota'],
                                'icms_aliquota_reduzida': row['icms_aliquota_reduzida'],
                                'protege_id': row['protege'],
                                'cbenef_id': row['cbenef'] if row['cbenef'] in valid_cbenefs else None,
                                'piscofins_cst': piscofins_cst,
                                'pis_aliquota': pis_aliquota,
                                'cofins_aliquota': cofins_aliquota,
                                'naturezareceita_id': natureza_receita_id,
                                'is_active': True,
                                'is_pending_sync': True,
                                'updated_at': current_time,
                                'user_updated': user,
                            }

                            if row['codigo'] in existing_items:
                                item = existing_items[row['codigo']]
                                for key, value in item_data.items():
                                    setattr(item, key, value)
                                items_to_update.append(item)
                            else:
                                new_item = Item(**item_data)
                                items_to_create.append(new_item)

                        except (ObjectDoesNotExist, ValidationError, TypeError, ValueError) as e:
                            error_message = f"Erro na linha {index + 2}: {e}"
                            self.logger.error(error_message)
                            errors.append(error_message)

                    if errors:
                        end_time = time.time()
                        elapsed_time = round(end_time - start_time, 3)
                        return JsonResponse({
                            'message': 'Erros encontrados durante o processamento do arquivo.',
                            'errors': errors,
                            'elapsed_time': elapsed_time
                        }, status=400)

                    for i in range(0, len(items_to_create), batch_size):
                        batch = items_to_create[i:i + batch_size]
                        Item.objects.bulk_create(batch, ignore_conflicts=True)

                    if items_to_update:
                        for i in range(0, len(items_to_update), batch_size):
                            batch = items_to_update[i:i + batch_size]
                            Item.objects.bulk_update(batch, fields=[
                                'barcode', 'description', 'ncm', 'cest', 'cfop_id', 'icms_cst_id', 
                                'icms_aliquota_id', 'icms_aliquota_reduzida', 'protege_id', 'cbenef_id', 
                                'piscofins_cst', 'pis_aliquota', 'cofins_aliquota', 'naturezareceita_id', 
                                'is_active', 'is_pending_sync', 'updated_at', 'user_updated'
                            ])

            except (pd.errors.ParserError, KeyError, TypeError, ValueError) as e:
                self.logger.error(f"Error processing Excel file: {e}")  
                return JsonResponse({'error': f"Erro ao processar o arquivo Excel: {e}"}, status=400)

            except ObjectDoesNotExist as e:
                self.logger.error(f"Object not found error: {e}")
                return JsonResponse({'error': 'Erro ao encontrar objetos relacionados no banco de dados.'}, status=400)

            except OperationalError as e:  # Add for database connection errors
                self.logger.error(f"Database error: {e}")
                return JsonResponse({'error': 'Erro no banco de dados. Tente novamente mais tarde.'}, status=500)

            except Exception as e:  # Catch any unexpected exceptions
                self.logger.critical(f"Unexpected error: {e}", exc_info=True)  # Log with traceback
                return JsonResponse({'error': 'Erro interno no servidor.'}, status=500)
            # except Exception as e:
            #     self.logger.error(f"Erro durante o processamento do arquivo: {e}")
            #     return JsonResponse({'error': f"Erro durante o processamento do arquivo: {e}"}, status=500)

            end_time = time.time()
            elapsed_time = round(end_time - start_time, 3)

            return JsonResponse({
                'message': 'Todos os itens foram salvos/atualizados com sucesso!',
                'processed_rows': len(df),
                'elapsed_time': elapsed_time
            })

        self.logger.error(f"Form inválido: {form.errors}")
        return JsonResponse({'errors': form.errors}, status=400)
   