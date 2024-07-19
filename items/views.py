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
from django.conf import settings
from django.core.exceptions import ValidationError, ObjectDoesNotExist
from django.views.decorators.csrf import csrf_exempt
from django.contrib import messages
from django.urls import reverse_lazy
from django.db import transaction, connection
from django.db.models import Value, CharField, OuterRef,  Subquery
from django.db.models.functions import Trim
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.db.utils import DataError
from django.apps import apps  # Adicione esta linha para importar o módulo apps
from django.core.exceptions import FieldDoesNotExist
from django.views import View
from django.views.generic import ListView, CreateView, UpdateView, DeleteView, DetailView
from django.contrib.auth.models import User
from clients.models import Client
from .models import Item, ImportedItem
from .forms import ItemForm, CSVUploadForm, ImportedItemForm
from impostos.models import IcmsCst, IcmsAliquota, IcmsAliquotaReduzida, Protege, CBENEF, PisCofinsCst, NaturezaReceita, Cfop
from django.http import JsonResponse, StreamingHttpResponse
from django.views.decorators.http import require_GET, require_POST
from .models import Item, ImportedItem
from itertools import chain
from django.db.models import Q, F
import openpyxl
from openpyxl import load_workbook, Workbook
from openpyxl.utils import get_column_letter
from io import BytesIO
from auditlog.models import LogEntry
from auditlog.registry import auditlog
from app.utils import get_auditlog_history

ACTION_MAPPING = {
    LogEntry.Action.CREATE: 'Criação',
    LogEntry.Action.UPDATE: 'Atualização',
    LogEntry.Action.DELETE: 'Exclusão'
}

def convert_to_decimal(number_str):
    try:
        # Substituir vírgula por ponto e converter para float
        return float(number_str.replace(',', '.'))
    except ValueError:
        # Lidar com valores inválidos
        return None

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
                if k not in ['client','user_updated', 'user_created', 'is_pending_sync', 'id']
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

        local_timestamp = timezone.localtime(log.timestamp)

        # Usa changes_display_dict para obter nomes de campos amigáveis
        # changes_display = log.changes_display_dict

        # print(changes_display)
        # print(filtered_changes)
        # # Filtra os changes_display para corresponder aos filtered_changes
        # mapped_changes = {}
        # changes_display_list = list(changes_display.keys())
        # aux = 0
        # for k, v in filtered_changes.items():
        #     display_name = filtered_changes.get(k, k)  # Obtém o nome amigável do campo
        #     mapped_changes[changes_display_list[aux]] = v
        #     aux += 1
        
        log_entry = {
            'action': ACTION_MAPPING.get(log.action, log.get_action_display()),
            'actor': log.actor.get_full_name() if log.actor else 'Unknown',
            'timestamp': local_timestamp.strftime('%d/%m/%Y %H:%M'),
            'changes': filtered_changes,
        }
        logs_data.append(log_entry)

    return JsonResponse({'logs': logs_data})

def export_items_to_excel(request, client_id, table):
    # Obter o cliente
    client = get_object_or_404(Client, id=client_id)

    # Verificar o valor de table e obter os itens adequados
    if table == 'all':
        items = Item.objects.filter(client=client).values(
            'client__name', 'code', 'barcode', 'description', 'ncm', 'cest',
            'cfop__cfop', 'icms_cst__code', 'icms_aliquota__code', 'icms_aliquota_reduzida',
            'protege__code', 'cbenef__code', 'piscofins_cst__code', 'pis_aliquota',
            'cofins_aliquota', 'naturezareceita__code', 'type_product', 'other_information'
        )
    elif table == 'await':
        items = Item.objects.filter(client=client, status_item__in=[1, 2]).values(
            'client__name', 'code', 'barcode', 'description', 'ncm', 'cest',
            'cfop__cfop', 'icms_cst__code', 'icms_aliquota__code', 'icms_aliquota_reduzida',
            'protege__code', 'cbenef__code', 'piscofins_cst__code', 'pis_aliquota',
            'cofins_aliquota', 'naturezareceita__code', 'type_product', 'other_information', 'await_sync_at', 'sync_at'
        )        
    elif table == 'new':
        items = ImportedItem.objects.filter(client=client, status_item=0).values(
            'client__name', 'code', 'barcode', 'description', 'ncm', 'cest',
            'cfop', 'icms_cst', 'icms_aliquota', 'icms_aliquota_reduzida',
            'protege', 'cbenef', 'piscofins_cst', 'pis_aliquota',
            'cofins_aliquota', 'naturezareceita', 'await_sync_at', 'sync_at' 
        )
    elif table == 'divergent':
        # Queryset de itens importados
        imported_items_queryset = ImportedItem.objects.filter(
            client=client, status_item=1, is_pending=True
        ).annotate(
            origem=Value('Integração', output_field=CharField())
        ).values(
            'client__name', 'code', 'barcode', 'description', 'ncm', 'cest',
            'cfop', 'icms_cst', 'icms_aliquota', 'icms_aliquota_reduzida',
            'protege', 'cbenef', 'piscofins_cst', 'pis_aliquota',
            'cofins_aliquota', 'naturezareceita'
        )

        # Subquery para obter os dados da base de itens correspondentes
        items_subquery = Item.objects.filter(
            client=client, code=OuterRef('code')
        ).annotate(
            piscofins_cst_code=F('piscofins_cst__code')
        ).values(
            'barcode', 'description', 'ncm', 'cest', 'cfop__cfop', 'icms_cst__code',
            'icms_aliquota__code', 'icms_aliquota_reduzida', 'protege__code',
            'cbenef__code', 'piscofins_cst_code', 'pis_aliquota', 'cofins_aliquota',
            'naturezareceita__code', 'type_product', 'other_information'
        )

        # Combinar os querysets usando um left outer join
        combined_queryset = imported_items_queryset.annotate(
            barcode_base=Subquery(items_subquery.values('barcode')[:1]),
            description_base=Subquery(items_subquery.values('description')[:1]),
            ncm_base=Subquery(items_subquery.values('ncm')[:1]),
            cest_base=Subquery(items_subquery.values('cest')[:1]),
            cfop_base=Subquery(items_subquery.values('cfop__cfop')[:1]),
            icms_cst_base=Subquery(items_subquery.values('icms_cst__code')[:1]),
            icms_aliquota_base=Subquery(items_subquery.values('icms_aliquota__code')[:1]),
            icms_aliquota_reduzida_base=Subquery(items_subquery.values('icms_aliquota_reduzida')[:1]),
            protege_base=Subquery(items_subquery.values('protege__code')[:1]),
            cbenef_base=Subquery(items_subquery.values('cbenef__code')[:1]),
            piscofins_cst_base=Subquery(items_subquery.values('piscofins_cst_code')[:1]),
            pis_aliquota_base=Subquery(items_subquery.values('pis_aliquota')[:1]),
            cofins_aliquota_base=Subquery(items_subquery.values('cofins_aliquota')[:1]),
            naturezareceita_base=Subquery(items_subquery.values('naturezareceita__code')[:1]), 
            type_product=Subquery(items_subquery.values('type_product')[:1]),
            other_information=Subquery(items_subquery.values('other_information')[:1])
        ).order_by('description', 'origem')

        # Converter para DataFrame (se necessário)
        df = pd.DataFrame(list(combined_queryset))
        
        # Ordem desejada das colunas
        desired_order = [
            'client__name', 'code', 'barcode_base', 'barcode', 
            'description_base', 'description', 'ncm_base', 'ncm',
            'cest_base', 'cest', 'cfop_base', 'cfop', 'icms_cst_base', 'icms_cst',
            'icms_aliquota_base', 'icms_aliquota', 'icms_aliquota_reduzida_base', 'icms_aliquota_reduzida', 
            'protege_base', 'protege', 'cbenef_base', 'cbenef', 'piscofins_cst_base', 'piscofins_cst', 
            'pis_aliquota_base', 'pis_aliquota', 'cofins_aliquota_base', 'cofins_aliquota',
            'naturezareceita_base', 'naturezareceita', 'type_product', 'other_information'
        ]

        # Reorganizando as colunas
        df = df.reindex(columns=desired_order)
        
        
        # Renomear colunas adicionando sufixo _cliente, exceto para code e client__name
        new_column_names = {col: (col + '_cliente' if '_base' not in col and col not in ['code', 'client__name'] else col) for col in df.columns}

        # Adicionar a renomeação de type_product para tipo_produto
        new_column_names['type_product'] = 'tipo_produto'
        new_column_names['other_information'] = 'outros_detalhes'

        # Renomear as colunas do DataFrame
        df = df.rename(columns=new_column_names)    
                     
    else:
        items = []

    # Converter para DataFrame
    if table != 'divergent':
        df = pd.DataFrame(list(items))
        
        if table == 'new':
            df['tipo_produto'] = ''
            df['outros_detalhes'] = ''
        
        if table == 'await':
            df.columns = [
                'Cliente', 'codigo', 'barcode', 'description', 'ncm', 'cest', 'cfop',
                'icms_cst', 'icms_aliquota', 'icms_aliquota_reduzida', 'protege', 'cbenef',
                'piscofins_cst', 'pis_aliquota', 'cofins_aliquota', 'naturezareceita',
                'tipo_produto', 'outros_detalhes', 'a_enviar', 'enviado_em'
            ]             
        else:
            df.columns = [
                'Cliente', 'codigo', 'barcode', 'description', 'ncm', 'cest', 'cfop',
                'icms_cst', 'icms_aliquota', 'icms_aliquota_reduzida', 'protege', 'cbenef',
                'piscofins_cst', 'pis_aliquota', 'cofins_aliquota', 'naturezareceita',
                'tipo_produto', 'outros_detalhes'
            ]        

    # Salvar o DataFrame em um arquivo Excel
    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    
    if table == 'new':
        response['Content-Disposition'] = f'attachment; filename=items_Novos_{client.name}.xlsx'
    elif table == 'divergent':
        response['Content-Disposition'] = f'attachment; filename=items_Divergentes_{client.name}.xlsx'
    elif table == 'await':
        response['Content-Disposition'] = f'attachment; filename=items_Aguardando_{client.name}.xlsx'        
    else:
        response['Content-Disposition'] = f'attachment; filename=items_{client.name}.xlsx'
        
    df.to_excel(response, index=False, sheet_name='Items')

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
    codes_param = request.GET.get('codes[]')  # Check for multiple codes first
    client = request.GET.get('client')

    if codes_param:
        codes = codes_param.split(',')  # Split comma-separated string if multiple codes
    else:
        code = request.GET.get('code')  # Check for a single code
        codes = [code] if code else []  # Create a list even if it's a single code

    if not codes or not client:
        return JsonResponse({'success': False, 'message': 'Code(s) and client are required.'})

    # Convert codes to integers for efficient database query
    try:
        codes = [int(code) for code in codes]
    except ValueError:
        return JsonResponse({'success': False, 'message': 'Invalid code format.'})

    # Check for existing codes in the database (bulk query)
    existing_codes = Item.objects.filter(code__in=codes, client=client).values_list('code', flat=True)

    # Determine invalid codes
    invalid_codes = [code for code in codes if code in existing_codes]

    if invalid_codes:
        return JsonResponse({'success': False, 'invalidCodes': invalid_codes})
    else:
        return JsonResponse({'success': True})

# def validate_item(request):
#     code = request.GET.get('code')
#     client = request.GET.get('client')

#     if not code or not client:
#         return JsonResponse({'success': False, 'message': 'Code and client are required.'})

#     exists = Item.objects.filter(code=code, client=client).exists()
#     if exists:
#         return JsonResponse({'success': False, 'message': 'This code for this client already exists.'})
    
#     return JsonResponse({'success': True, 'message': 'This code for this client is available.'})

@method_decorator(login_required(login_url='login'), name='dispatch')
class ItemListView(ListView):
    model = Item
    template_name = 'list_item.html'
    context_object_name = 'items'
    paginate_by = 50  # Defina quantos itens você quer por página

    def get_queryset(self):
        client_id = self.kwargs.get('client_id')
        client = get_object_or_404(Client, id=client_id)

        queryset = Item.objects.filter(client=client).order_by('description')
        # Filter with ForeignKey lookups and other fields
        filter_kwargs = {}
        for field_name in ['code', 'barcode', 'description', 'ncm', 'cest', 'icms_aliquota_reduzida', 'pis_aliquota', 'cofins_aliquota', 'type_product']:
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

@method_decorator(login_required(login_url='login'), name='dispatch')
class ImportedItemListViewNewItem(ListView):
    model = ImportedItem
    template_name = 'handsome_new_imported_items.html'
    # template_name = 'list_imported_items.html'
    context_object_name = 'imported_items'
    paginate_by = 50  # Defina quantos itens você quer por página

    def get_queryset(self):
        client_id = self.kwargs.get('client_id')
        client = get_object_or_404(Client, id=client_id)

        queryset = ImportedItem.objects.filter(client=client, status_item=0, is_pending=True).order_by('description')  
        
        # Adicionar filtros baseados nos parâmetros GET, exceto 'page'
        filters = self.request.GET.dict()
        filters.pop('page', None)  # Remover o parâmetro 'page' dos filtros
        for key, value in filters.items():
            if key and value:
                queryset = queryset.filter(Q(**{key: value}))
                
        # Salva o total de itens no queryset combinado
        self.total_items = queryset.count()
        
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        client = get_object_or_404(Client, id=self.kwargs.get('client_id'))
        context['client'] = client
        context['client_name'] = client.name
        context['client_id'] = client.id
        context['filter_params'] = self.request.GET
        context['total_items'] = self.total_items
        icms_cst_choices = list(IcmsCst.objects.values_list('code', 'code'))  
        cfop_choices = list(Cfop.objects.values_list('cfop', 'description'))
        # Adicionando cbenef ao contexto
        context['cbenef_choices'] = CBENEF.objects.all()         
        context['icms_cst_choices'] = icms_cst_choices        
        context['cfop_choices'] = cfop_choices
        context['protege_choices'] = Protege.objects.all()
        context['piscofins_choices'] = PisCofinsCst.objects.all()
        context['naturezareceita_choices'] = NaturezaReceita.objects.all()
        context['icmsaliquota_choices'] = IcmsAliquota.objects.all()
        icmsaliquotareduzida_codes = IcmsAliquotaReduzida.objects.values_list('code', flat=True)
        context['icmsaliquotareduzida_codes'] = set(icmsaliquotareduzida_codes)
        context['form'] = ImportedItemForm()
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
    
# @method_decorator(login_required(login_url='login'), name='dispatch')
# class ImportedItemListViewDivergentItem(ListView):
#     model = ImportedItem
#     template_name = 'list_imported_divergent_items.html'
#     context_object_name = 'imported_items'
#     paginate_by = 50  # Defina quantos itens você quer por página

#     def get_queryset(self):
#         client_id = self.kwargs.get('client_id')
#         client = get_object_or_404(Client, id=client_id)
#         filters = self.request.GET.dict()
        
#         # Anota os querysets com a coluna 'origem'
#         imported_items_queryset = ImportedItem.objects.filter(
#             client=client, status_item=1, is_pending=True
#         ).annotate(origem=Value('Integração', output_field=CharField()))
        
#         # Separar filtros baseados nos parâmetros GET
#         base_filters = {key[5:]: value for key, value in filters.items() if key.startswith('base-')}
#         cliente_filters = {key[8:]: value for key, value in filters.items() if key.startswith('cliente-')}
        
#         # Aplicar filtros ao imported_items_queryset
#         for key, value in cliente_filters.items():
#             imported_items_queryset = imported_items_queryset.filter(Q(**{key: value}))        

#         items_queryset = Item.objects.filter(
#             client=client, code__in=imported_items_queryset.values('code')
#         ).annotate(
#             origem=Value('Base', output_field=CharField()),
#             piscofins_cst_code=F('piscofins_cst__code')  # Acesso ao campo 'code' de piscofins_cst
#         ).order_by('description')
        
#         # Aplicar filtros ao items_queryset
#         for key, value in base_filters.items():
#             items_queryset = items_queryset.filter(Q(**{key: value}))

#         # Combine os querysets e ordena por 'description' e 'origem'
#         combined_queryset = sorted(
#             chain(imported_items_queryset, items_queryset),
#             key=lambda item: (item.description, item.origem)
#         )
        
#         return combined_queryset
   
#     def get_context_data(self, **kwargs):
#         context = super().get_context_data(**kwargs)
#         client = get_object_or_404(Client, id=self.kwargs.get('client_id'))
#         context['client'] = client
#         context['client_name'] = client.name
#         context['client_id'] = client.id
#         context['filter_params'] = self.request.GET
#         icms_cst_choices = list(IcmsCst.objects.values_list('code', 'code'))  
#         cfop_choices = list(Cfop.objects.values_list('cfop', 'description'))
#         # Adicionando cbenef ao contexto
#         context['cbenef_choices'] = CBENEF.objects.all()         
#         context['icms_cst_choices'] = icms_cst_choices        
#         context['cfop_choices'] = cfop_choices
#         context['protege_choices'] = Protege.objects.all()
#         context['piscofins_choices'] = PisCofinsCst.objects.all()
#         context['naturezareceita_choices'] = NaturezaReceita.objects.all()
#         context['icmsaliquota_choices'] = IcmsAliquota.objects.all()
#         icmsaliquotareduzida_codes = IcmsAliquotaReduzida.objects.values_list('code', flat=True)
#         context['icmsaliquotareduzida_codes'] = set(icmsaliquotareduzida_codes)
#         context['form'] = ImportedItemForm()
#         # Adiciona os cálculos de paginação
#         paginator = context['paginator']
#         page_obj = context['page_obj']
#         total_pages = paginator.num_pages
#         current_page = page_obj.number

#         if total_pages <= 10:
#             page_range = range(1, total_pages + 1)
#         else:
#             if current_page <= 4:
#                 page_range = list(range(1, 6)) + ['...'] + [total_pages - 1, total_pages]
#             elif current_page > total_pages - 4:
#                 page_range = [1, 2, '...'] + list(range(total_pages - 4, total_pages + 1))
#             else:
#                 page_range = [1, 2, '...'] + list(range(current_page - 2, current_page + 3)) + ['...'] + [total_pages - 1, total_pages]

#         context['page_range'] = page_range
#         return context    

@method_decorator(login_required(login_url='login'), name='dispatch')
class ImportedItemListViewAwaitSyncItem(ListView):
    model = ImportedItem
    template_name = 'handsome_await_imported_items.html'
    # template_name = 'list_imported_items.html'
    context_object_name = 'imported_items'
    paginate_by = 100  # Defina quantos itens você quer por página

    def get_queryset(self):
        client_id = self.kwargs.get('client_id')
        client = get_object_or_404(Client, id=client_id)

        queryset = Item.objects.filter(client=client, status_item__in=[1, 2]).order_by('description')  
        
        # Adicionar filtros baseados nos parâmetros GET, exceto 'page'
        filters = self.request.GET.dict()
        filters.pop('page', None)  # Remover o parâmetro 'page' dos filtros
        for key, value in filters.items():
            if key and value:
                queryset = queryset.filter(Q(**{key: value}))
                
        # Salva o total de itens no queryset combinado
        self.total_items = queryset.count()
        
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        client = get_object_or_404(Client, id=self.kwargs.get('client_id'))
        context['client'] = client
        context['client_name'] = client.name
        context['client_id'] = client.id
        context['filter_params'] = self.request.GET
        context['total_items'] = self.total_items
        icms_cst_choices = list(IcmsCst.objects.values_list('code', 'code'))  
        cfop_choices = list(Cfop.objects.values_list('cfop', 'description'))
        # Adicionando cbenef ao contexto
        context['cbenef_choices'] = CBENEF.objects.all()         
        context['icms_cst_choices'] = icms_cst_choices        
        context['cfop_choices'] = cfop_choices
        context['protege_choices'] = Protege.objects.all()
        context['piscofins_choices'] = PisCofinsCst.objects.all()
        context['naturezareceita_choices'] = NaturezaReceita.objects.all()
        context['icmsaliquota_choices'] = IcmsAliquota.objects.all()
        icmsaliquotareduzida_codes = IcmsAliquotaReduzida.objects.values_list('code', flat=True)
        context['icmsaliquotareduzida_codes'] = set(icmsaliquotareduzida_codes)
        context['form'] = ImportedItemForm()
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


@csrf_exempt
def save_imported_item(request):
    if request.method == 'POST':
        try:
            data = request.POST
            print(data)
            # Extract data from the request
            tipo_produto = data.get('fix_item', '');
            code = data.get('code', '').strip()
            client_id = data.get('client', '')
            barcode = data.get('barcode', '').strip()
            description = data.get('description', '')
            ncm = data.get('ncm', '').strip()
            cest = data.get('cest', '').strip()
            cfop_code = data.get('cfop', '')
            icms_cst_code = data.get('icms_cst', '')
            icms_aliquota_code = data.get('icms_aliquota', '')
            icms_aliquota_reduzida = data.get('icms_aliquota_reduzida', '')
            cbenef_code = data.get('cbenef', '')
            cbenef_instance = None
            protege = data.get('protege', '')
            piscofins_cst = data.get('piscofins_cst', '')
            pis_aliquota_str = data.get('pis_aliquota', '')
            cofins_aliquota_str = data.get('cofins_aliquota', '')
            naturezareceita_id = data.get('naturezareceita', '')
            naturezareceita_instance = None
            type_product = data.get('type_product', '')
            
            pis_aliquota = convert_to_decimal(pis_aliquota_str)
            cofins_aliquota = convert_to_decimal(cofins_aliquota_str)
            
            # Verificar se o client_id é válido
            client = get_object_or_404(Client, id=client_id)  
            cfop = get_object_or_404(Cfop, cfop=cfop_code)          
            icms_cst = get_object_or_404(IcmsCst, code=icms_cst_code)
            icms_aliquota = get_object_or_404(IcmsAliquota, code=icms_aliquota_code)
            protege = get_object_or_404(Protege, code=protege)
            piscofins_cst = get_object_or_404(PisCofinsCst, code=piscofins_cst)
            
            
            if cbenef_code:
                cbenef_instance = get_object_or_404(CBENEF, code=cbenef_code)
                
            if naturezareceita_id:
                naturezareceita_instance = get_object_or_404(NaturezaReceita, id=naturezareceita_id)
                

            with transaction.atomic():
                if tipo_produto == '1':
                    # Atualiza o item existente se tipo_produto for igual a 1
                    item = get_object_or_404(Item, code=code, client=client)
                    item.barcode = barcode
                    item.description = description
                    item.ncm = ncm
                    item.cest = cest
                    item.cfop = cfop
                    item.icms_cst = icms_cst
                    item.icms_aliquota = icms_aliquota
                    item.icms_aliquota_reduzida = icms_aliquota_reduzida
                    item.cbenef = cbenef_instance
                    item.protege = protege
                    item.piscofins_cst = piscofins_cst
                    item.pis_aliquota = pis_aliquota
                    item.cofins_aliquota = cofins_aliquota
                    item.naturezareceita = naturezareceita_instance
                    item.type_product = type_product
                    item.status_item = 2  # Verifique se precisa atualizar o status do item
                    item.save()

                    # Update the ImportedItem model
                    ImportedItem.objects.filter(code=code, client=client).update(is_pending=False)
                else:
                    # Cria um novo item se tipo_produto não for igual a 1
                    item = Item(
                        code=code,
                        client=client,
                        barcode=barcode,
                        description=description,
                        ncm=ncm,
                        cest=cest,
                        cfop=cfop,
                        icms_cst=icms_cst,
                        icms_aliquota=icms_aliquota,
                        icms_aliquota_reduzida=icms_aliquota_reduzida,
                        cbenef=cbenef_instance,
                        protege=protege,
                        piscofins_cst=piscofins_cst,
                        pis_aliquota=pis_aliquota,
                        cofins_aliquota=cofins_aliquota,
                        naturezareceita=naturezareceita_instance,
                        type_product=type_product,
                        status_item=2  # Verifique se precisa definir o status do item
                    )
                    item.save()

                    # Update the ImportedItem model
                    ImportedItem.objects.filter(code=code, client=client).update(is_pending=False)


            # Return a success response
            return JsonResponse({'status': 'success', 'message': 'Item saved successfully'})
        
        except Exception as e:
            # Handle exceptions
            print(str(e))
            return JsonResponse({'status': 'error', 'message': str(e)})

    return JsonResponse({'status': 'error', 'message': 'Invalid request method'})

@csrf_exempt
def save_bulk_imported_item(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.POST.get('items', '[]'))
            
            # print(data)
            # return JsonResponse({'status': 'error', 'message': 'rrro'})
            
            # Validate each item and collect errors if any
            all_errors = []
            for i, row in enumerate(data):
                item_data = {
                    'code': row[0],
                    'barcode': row[1],
                    'description': row[2],
                    'ncm': row[3],
                    'cest': row[4],
                    'cfop': row[5],
                    'icms_cst': row[6],
                    'icms_aliquota': row[7],
                    'icms_aliquota_reduzida': row[8],
                    'cbenef': row[9],
                    'protege': row[10],
                    'piscofins_cst': row[11],
                    'pis_aliquota': row[12],
                    'cofins_aliquota': row[13],
                    'naturezareceita': row[17],
                    'type_product': row[15],
                    'fix_item': row[16]  # Get fix_item from the last column
                }              
                errors = validate_item_data(item_data)
                if errors:
                    all_errors.extend([f"Linha {i + 1}: {err}" for err in errors])

            if all_errors:
                return JsonResponse({'status': 'error', 'message': '\n'.join(all_errors)})

            
            # If all items are valid, process them
            with transaction.atomic():
                for row in data:
                    tipo_produto = row[16]
                    code = row[0]
                    client_id = row[18]
                    barcode = row[1]
                    description = row[2]
                    ncm = row[3]
                    cest = row[4]
                    cfop_code = row[5]
                    icms_cst_code = row[6]
                    icms_aliquota_code = row[7]
                    icms_aliquota_reduzida = row[8]
                    cbenef_code = row[9]
                    cbenef_instance = None
                    protege = row[10]
                    piscofins_cst = row[11]
                    pis_aliquota_str = row[12]
                    cofins_aliquota_str = row[13]
                    naturezareceita_id = row[17]
                    naturezareceita_instance = None
                    type_product = row[15]
                    
                    pis_aliquota = convert_to_decimal(pis_aliquota_str)
                    cofins_aliquota = convert_to_decimal(cofins_aliquota_str)
                                        
                    # Verificar se o client_id é válido
                    client = get_object_or_404(Client, id=client_id)  
                    cfop = get_object_or_404(Cfop, cfop=cfop_code)          
                    icms_cst = get_object_or_404(IcmsCst, code=icms_cst_code)
                    icms_aliquota = get_object_or_404(IcmsAliquota, code=icms_aliquota_code)
                    protege = get_object_or_404(Protege, code=protege)
                    piscofins_cst = get_object_or_404(PisCofinsCst, code=piscofins_cst)
                    
                    if cbenef_code:
                        cbenef_instance = get_object_or_404(CBENEF, code=cbenef_code)
                    
                    if naturezareceita_id:
                        naturezareceita_instance = get_object_or_404(NaturezaReceita, id=naturezareceita_id)                    
                    
                    user = request.user
                    current_time = timezone.now()  
                    
                    # return JsonResponse({'status': 'error', 'message': 'rrro'})                           
                    
                    if tipo_produto == '1':
                        # Atualiza o item existente se tipo_produto for igual a 1
                        item = get_object_or_404(Item, code=code, client=client)
                        item.barcode = barcode
                        item.description = description
                        item.ncm = ncm
                        item.cest = cest
                        item.cfop = cfop
                        item.icms_cst = icms_cst
                        item.icms_aliquota = icms_aliquota
                        item.icms_aliquota_reduzida = icms_aliquota_reduzida
                        item.cbenef = cbenef_instance
                        item.protege = protege
                        item.piscofins_cst = piscofins_cst
                        item.pis_aliquota = pis_aliquota
                        item.cofins_aliquota = cofins_aliquota
                        item.naturezareceita = naturezareceita_instance
                        item.type_product = type_product
                        item.status_item = 1  # Verifique se precisa atualizar o status do item
                        item.updated_at= current_time
                        item.await_sync_at = current_time
                        item.user_updated = user                        
                        item.save()

                        # Update the ImportedItem model
                        ImportedItem.objects.filter(code=code, client=client).update(is_pending=False)
                    else:
                        sequencial = row[19]
                        estado_origem = row[20]
                        estado_destino = row[21]
                        
                        # Cria um novo item se tipo_produto não for igual a 1
                        item = Item(
                            code=code,
                            client=client,
                            barcode=barcode,
                            description=description,
                            ncm=ncm,
                            cest=cest,
                            cfop=cfop,
                            icms_cst=icms_cst,
                            icms_aliquota=icms_aliquota,
                            icms_aliquota_reduzida=icms_aliquota_reduzida,
                            cbenef=cbenef_instance,
                            protege=protege,
                            piscofins_cst=piscofins_cst,
                            pis_aliquota=pis_aliquota,
                            cofins_aliquota=cofins_aliquota,
                            naturezareceita=naturezareceita_instance,
                            type_product=type_product,
                            sequencial=sequencial,
                            estado_origem=estado_origem,
                            estado_destino=estado_destino,
                            created_at= current_time,
                            updated_at= current_time,
                            await_sync_at = current_time,
                            user_created = user,
                            user_updated = user,
                            status_item=1  # Verifique se precisa definir o status do item
                        )
                        item.save()

                        # Update the ImportedItem model
                        ImportedItem.objects.filter(code=code, client=client).update(is_pending=False)

            # Return a success response
            return JsonResponse({'status': 'success', 'message': 'Itens salvos com sucesso'})

        except json.JSONDecodeError:
            return JsonResponse({'status': 'error', 'message': 'Invalid JSON data format'})

    return JsonResponse({'status': 'error', 'message': 'Invalid request method'})

class XLSXUploadView(View):
    template_name = 'upload_items.html'
    logger = logging.getLogger(__name__)  # Configurar o logger
    
    TYPE_PRODUCT_CHOICES = {
        'Revenda': 'Revenda',
        'Imobilizado': 'Imobilizado',
        'Insumos': 'Insumos',
    }   
    
    REQUIRED_COLUMNS = [
        'codigo', 'barcode', 'description', 'ncm', 'cest', 'cfop', 'icms_cst', 
        'icms_aliquota', 'icms_aliquota_reduzida', 'piscofins_cst', 'naturezareceita', 
        'protege', 'cbenef', 'tipo_produto', 'outros_detalhes'
    ]     

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
                df = pd.read_excel(xlsx_file, dtype={
                    'ncm': str, 
                    'cest': str, 
                    'barcode': str, 
                    'naturezareceita': str,
                    'tipo_produto': str,  # Adicionar tipo_produto
                })

                # Verificação das colunas obrigatórias
                missing_columns = [col for col in self.REQUIRED_COLUMNS if col not in df.columns]
                if missing_columns:
                    end_time = time.time()
                    elapsed_time = round(end_time - start_time, 3)
                     
                    error_message = [f"Erro: As seguintes colunas estão faltando no arquivo Excel: {', '.join(missing_columns)}"]
                    self.logger.error(error_message)
                    # return JsonResponse({'error': error_message}, status=400)
                    return JsonResponse({
                        'message': 'Colunas faltantes.',
                        'errors': error_message,
                        'elapsed_time': elapsed_time
                    }, status=400)                 
                
                
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
                
                # Adicionando a transformação e validação de tipo_produto
                df['tipo_produto'] = df['tipo_produto'].str.capitalize().str.strip()
                valid_tipo_produto = set(self.TYPE_PRODUCT_CHOICES.keys())
                invalid_tipo_produto = df[~df['tipo_produto'].isin(valid_tipo_produto)]

                if not invalid_tipo_produto.empty:
                    invalid_details = [
                        f"Erro na linha {index + 2} [tipo_produto]: {row['tipo_produto']} é um valor inválido."
                        for index, row in invalid_tipo_produto.iterrows()
                    ]
                    end_time = time.time()
                    elapsed_time = round(end_time - start_time, 3)
                    return JsonResponse({
                        'message': 'Linhas inválidas encontradas.',
                        'errors': invalid_details,
                        'elapsed_time': elapsed_time
                    }, status=400)                

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

                batch_size = 500

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
                                'code': str(row['codigo']).strip(),
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
                                'type_product': self.TYPE_PRODUCT_CHOICES[row['tipo_produto']], 
                                'other_information': row['outros_detalhes'],
                                'is_active': True,
                                'is_pending_sync': True,
                                'updated_at': current_time,
                                'user_updated': user,
                            }

                            if str(row['codigo']).strip() in existing_items:
                                item = existing_items[str(row['codigo']).strip()]  # Converter para string
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
                                'type_product', 'other_information',
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

            end_time = time.time()
            elapsed_time = round(end_time - start_time, 3)

            return JsonResponse({
                'message': 'Todos os itens foram salvos/atualizados com sucesso!',
                'processed_rows': len(df),
                'elapsed_time': elapsed_time
            })

        self.logger.error(f"Form inválido: {form.errors}")
        return JsonResponse({'errors': form.errors}, status=400)
   
def validate_item_data(item_data):
    errors = []

    # Add validation rules for each field (similar to your individual item validation)
    if not item_data.get('description'):
        errors.append("A descrição é obrigatória.")
    # ... other validation rules ...

    return errors

@method_decorator(login_required(login_url='login'), name='dispatch')
class ImportedItemListViewDivergentItemExcelVersion(ListView):
    model = ImportedItem
    template_name = 'handsome_divergent_imported_items.html'
    context_object_name = 'imported_items'
    paginate_by = 100  # Defina quantos itens você quer por página

    def get_queryset(self):
        client_id = self.kwargs.get('client_id')
        client = get_object_or_404(Client, id=client_id)
        filters = self.request.GET.dict()
        
        # codigos_desejados = [
        #     '57','64','66','70','79','86','2465','4049','4788','4800','4825','4915','4990','4992','4993','4994','4995','4996','4998','4999','5000','5002','5003','5004','5005','5006','5007','5008','5009','5010','5011','5012','5013','5014','5015','5016','5023','5039','5052','5087','5088','5138','5144','5175','5200','5203','5254','5295','5300','5803','5810','5814','5910','6129','6241','6305','6454','6532','6550','6579','7131','7149','7166','7257','7259','7262','7292','7354','7560','7584','7591','8008','8032','8375','8675','8754','8775','8844','8879','9064','9210','9279','9283','9284','9285','9416','9548','10003','10157','10194','10201','10203','10204','10211','10380','10956','11384','11534','12359','12474','12502','13022','13589','13914','14484','14981','15258','15452','15453','15524','15537','15623','16430','16983','17425','17535','18011','18272','18391','18689','20532','20599','20600','21060','22704','23298','23647','24061','24218','24219','25862','25863','25995','26065','26079','26436','26706','26708','26771','26941','27002','27305','27801','27802','28403','28464','28667','28836','29083','29208','29411','29465','29467','29931','30189','30191','30192','31197','31505','31506','31511','31526','32990','33243','33458','34241','34451','36300','36301','36800','37368','38223','41103','41196','41550','41552','41701','41835','41851','41852','44740','45124','46164','46177','46220','46221','46452','46923','47161','47414','47422','47423','48527','50171','50181','50254','50344','50345','50346','50583','50598','51489','52399','52526','52541','52938','53306','53878','54057','54300','54665','55046','55059','57552','57665','57666','58410','58419','58542','58667','59085','59579','60201','60321','60378','60385','60462','60747','60907','60933','60985','60989','60990','60991','61039','61040','61041','61499','61908','62234','62235','62238','62240','62244','62245','62246','62247','62257','62258','62695','63549','63702','64688','64689','64690','64692','64693','64694','64696','64697','64698','64699','64702','64705','64706','64707','64709','64710','64711','64712','64713','64714','64715','64716','64718','64719','64720','64721','64722','64723','64724','64725','64726','64727','64729','65139','65140','65141','65142','65143','65144','65145','65146','65147','65148','65149','65150','65151','65152','65153','65154','65155','65156','65157','65158','65159','65160','65207','65370','65393','65394','65397','65466','66133','66248','66249','66914','67738','67739','67740','67996','67997','67998','68524','70243','70244','70304','70998','71211','71304','71663','72056','72107','72194','72377','72482','72493','72582','72664','72731','72732','72753','72754','72757','72821','72822','72824','73374','73375','73376','73377','73502','73770','73902','73903','73904','73985','74101','74131','74132','74133','74134','74208','74404','74442','74498','74617','75595','75817','75818','76268','76675','76676','76230','76621','76622','76652','76669','76771','76948','76951','76958','77270','77278','77280','77745','77870','77871','77872','77874','77877','77879','77880','77881','77884','77885','77886','77887','77888','77889','77890','77891','77892','77893','77894','77895','77897','77900','77901','77902','77903','77904','77905','77906','77907','77908','77909','77910','77911','77912','77913','77914','77915','77916','77917','77918','77919','77920','77921','77922','77923','77924','77925','77926','77927','77928','77929','77931','77932','77933','77934','77940','77941','77942','77982','78008','78106','78163','78234','78253','78254','78255','78256','78257','78258','78259','78260','78264','78430','78439','78443','78477','78480','78499','78500','78501','78533','78580','78587','78588','78589','78623','78634','78638','78642','78650','78956','79000','79001','79069','79088','79089','79093','79107','79243','79244','79245','79479','79480','79614','79633','79649','79675','79798','79799','79889','79897','79921','80101','80147','80148','80467','80619','46203','80948','81164','81314','81440','81456','81528','81599','81600','81601','81602','81839','81864','81875','81891','81915','81960'
        # ]
        
        # Anota os querysets com a coluna 'origem'
        imported_items_queryset = ImportedItem.objects.filter(
            client=client, status_item=1, is_pending=True
        ).annotate(
            origem=Value('Integração', output_field=CharField())
        ).values(
            'client__name', 'code', 'barcode', 'description', 'ncm', 'cest',
            'cfop', 'icms_cst', 'icms_aliquota', 'icms_aliquota_reduzida',
            'protege', 'cbenef', 'piscofins_cst', 'pis_aliquota',
            'cofins_aliquota', 'naturezareceita'
        )
        
        # imported_items_queryset = ImportedItem.objects.filter(
        #     client=client,
        #     status_item=1,
        #     is_pending=True,
        #     code__in=codigos_desejados  # Filtrar pelos códigos desejados
        # ).annotate(
        #     origem=Value('Integração', output_field=CharField())
        # ).values(
        #     'client__name', 'code', 'barcode', 'description', 'ncm', 'cest',
        #     'cfop', 'icms_cst', 'icms_aliquota', 'icms_aliquota_reduzida',
        #     'protege', 'cbenef', 'piscofins_cst', 'pis_aliquota',
        #     'cofins_aliquota', 'naturezareceita'
        # )        
        
        # Separar filtros baseados nos parâmetros GET
        base_filters = {key[5:]: value for key, value in filters.items() if key.startswith('base-')}
        cliente_filters = {key[8:]: value for key, value in filters.items() if key.startswith('cliente-')}
        
        print(base_filters)
        print(cliente_filters)
        
        # Aplicar filtros ao imported_items_queryset
        for key, value in cliente_filters.items():
            imported_items_queryset = imported_items_queryset.filter(Q(**{key: value}))        

        items_queryset = Item.objects.filter(
            client=client, code__in=imported_items_queryset.values('code')
        ).annotate(
            origem=Value('Base', output_field=CharField()),
            piscofins_cst_code=F('piscofins_cst__code')  # Acesso ao campo 'code' de piscofins_cst
        ).order_by('description')
        
        # Subquery para obter os dados da base de itens correspondentes
        items_subquery = Item.objects.filter(
            client=client, code=OuterRef('code')
        ).annotate(
            piscofins_cst_code=F('piscofins_cst__code')
        ).values(
            'barcode', 'description', 'ncm', 'cest', 'cfop__cfop', 'icms_cst__code',
            'icms_aliquota__code', 'icms_aliquota_reduzida', 'protege__code',
            'cbenef__code', 'piscofins_cst_code', 'pis_aliquota', 'cofins_aliquota',
            'naturezareceita__code', 'type_product'
        )        
        
        # Aplicar filtros ao items_queryset
        for key, value in base_filters.items():
            items_queryset = items_queryset.filter(Q(**{key: value}))
            
        # Aplicar filtros ao items_subquery
        for key, value in base_filters.items():
            items_subquery = items_subquery.filter(Q(**{key: value}))            

        # Combinar os querysets usando um left outer join
        combined_queryset = imported_items_queryset.annotate(
            barcode_base=Subquery(items_subquery.values('barcode')[:1]),
            description_base=Subquery(items_subquery.values('description')[:1]),
            ncm_base=Subquery(items_subquery.values('ncm')[:1]),
            cest_base=Subquery(items_subquery.values('cest')[:1]),
            cfop_base=Subquery(items_subquery.values('cfop__cfop')[:1]),
            icms_cst_base=Subquery(items_subquery.values('icms_cst__code')[:1]),
            icms_aliquota_base=Subquery(items_subquery.values('icms_aliquota__code')[:1]),
            icms_aliquota_reduzida_base=Subquery(items_subquery.values('icms_aliquota_reduzida')[:1]),
            protege_base=Subquery(items_subquery.values('protege__code')[:1]),
            cbenef_base=Subquery(items_subquery.values('cbenef__code')[:1]),
            piscofins_cst_base=Subquery(items_subquery.values('piscofins_cst_code')[:1]),
            pis_aliquota_base=Subquery(items_subquery.values('pis_aliquota')[:1]),
            cofins_aliquota_base=Subquery(items_subquery.values('cofins_aliquota')[:1]),
            naturezareceita_base=Subquery(items_subquery.values('naturezareceita__code')[:1]), 
            type_product_base=Subquery(items_subquery.values('type_product')[:1]),       
        ).annotate(
            description_cliente=F('description')
        ).filter(
            Q(description_base=F('description_cliente'))
        ).order_by('description', 'origem')  
        
        # Reorganizar e renomear colunas adicionando sufixo _cliente, exceto para 'code' e 'client__name'
        combined_queryset = combined_queryset.values(
            'client__name',
            'code',
            'barcode_base',
            'barcode',
            'description_base',
            'description',
            'ncm_base',
            'ncm',
            'cest_base',
            'cest',
            'cfop_base',
            'cfop',
            'icms_cst_base',
            'icms_cst',
            'icms_aliquota_base',
            'icms_aliquota',
            'icms_aliquota_reduzida_base',
            'icms_aliquota_reduzida',
            'protege_base',
            'protege',
            'cbenef_base',
            'cbenef',
            'piscofins_cst_base',
            'piscofins_cst',
            'pis_aliquota_base',
            'pis_aliquota',
            'cofins_aliquota_base',
            'cofins_aliquota',
            'naturezareceita_base',
            'naturezareceita',
            'type_product_base'
        )
        
        # Salva o total de itens no queryset combinado
        self.total_items = combined_queryset.count()
        
        return [
            {
                **{key + '_cliente' if '_base' not in key and key not in ['code', 'client__name'] else key: value 
                for key, value in item.items()}
            }
            for item in combined_queryset
        ]  
    
   
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        client = get_object_or_404(Client, id=self.kwargs.get('client_id'))
        context['client'] = client
        context['client_name'] = client.name
        context['client_id'] = client.id
        context['filter_params'] = self.request.GET
        context['total_items'] = self.total_items
        icms_cst_choices = list(IcmsCst.objects.values_list('code', 'code'))  
        cfop_choices = list(Cfop.objects.values_list('cfop', 'description'))
        # Adicionando cbenef ao contexto
        context['cbenef_choices'] = CBENEF.objects.all()         
        context['icms_cst_choices'] = icms_cst_choices        
        context['cfop_choices'] = cfop_choices
        context['protege_choices'] = Protege.objects.all()
        context['piscofins_choices'] = PisCofinsCst.objects.all()
        context['naturezareceita_choices'] = NaturezaReceita.objects.all()
        context['icmsaliquota_choices'] = IcmsAliquota.objects.all()
        icmsaliquotareduzida_codes = IcmsAliquotaReduzida.objects.values_list('code', flat=True)
        context['icmsaliquotareduzida_codes'] = set(icmsaliquotareduzida_codes)
        context['form'] = ImportedItemForm()
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
class ImportedItemListViewDivergentDescriptionItemExcelVersion(ListView):
    model = ImportedItem
    template_name = 'handsome_description_imported_items.html'
    context_object_name = 'imported_items'
    paginate_by = 100  # Defina quantos itens você quer por página

    def get_queryset(self):
        client_id = self.kwargs.get('client_id')
        client = get_object_or_404(Client, id=client_id)
        filters = self.request.GET.dict()
        
        # Anota os querysets com a coluna 'origem'
        imported_items_queryset = ImportedItem.objects.filter(
            client=client, status_item=1, is_pending=True
        ).annotate(
            origem=Value('Integração', output_field=CharField())
        ).values(
            'client__name', 'code', 'barcode', 'description', 'ncm', 'cest',
            'cfop', 'icms_cst', 'icms_aliquota', 'icms_aliquota_reduzida',
            'protege', 'cbenef', 'piscofins_cst', 'pis_aliquota',
            'cofins_aliquota', 'naturezareceita'
        )
        
        # Separar filtros baseados nos parâmetros GET
        base_filters = {key[5:]: value for key, value in filters.items() if key.startswith('base-')}
        cliente_filters = {key[8:]: value for key, value in filters.items() if key.startswith('cliente-')}
        
        # Aplicar filtros ao imported_items_queryset
        for key, value in cliente_filters.items():
            imported_items_queryset = imported_items_queryset.filter(Q(**{key: value}))        

        items_queryset = Item.objects.filter(
            client=client, code__in=imported_items_queryset.values('code')
        ).annotate(
            origem=Value('Base', output_field=CharField()),
            piscofins_cst_code=F('piscofins_cst__code')  # Acesso ao campo 'code' de piscofins_cst
        ).order_by('description')
        # Subquery para obter os dados da base de itens correspondentes
        items_subquery = Item.objects.filter(
            client=client, code=OuterRef('code')
        ).annotate(
            piscofins_cst_code=F('piscofins_cst__code')
        ).values(
            'barcode', 'description', 'ncm', 'cest', 'cfop__cfop', 'icms_cst__code',
            'icms_aliquota__code', 'icms_aliquota_reduzida', 'protege__code',
            'cbenef__code', 'piscofins_cst_code', 'pis_aliquota', 'cofins_aliquota',
            'naturezareceita__code', 'type_product'
        )        
        
        # Aplicar filtros ao items_queryset
        for key, value in base_filters.items():
            items_queryset = items_queryset.filter(Q(**{key: value}))

        # Combinar os querysets usando um left outer join
        combined_queryset = imported_items_queryset.annotate(
            barcode_base=Subquery(items_subquery.values('barcode')[:1]),
            description_base=Subquery(items_subquery.values('description')[:1]),
            ncm_base=Subquery(items_subquery.values('ncm')[:1]),
            cest_base=Subquery(items_subquery.values('cest')[:1]),
            cfop_base=Subquery(items_subquery.values('cfop__cfop')[:1]),
            icms_cst_base=Subquery(items_subquery.values('icms_cst__code')[:1]),
            icms_aliquota_base=Subquery(items_subquery.values('icms_aliquota__code')[:1]),
            icms_aliquota_reduzida_base=Subquery(items_subquery.values('icms_aliquota_reduzida')[:1]),
            protege_base=Subquery(items_subquery.values('protege__code')[:1]),
            cbenef_base=Subquery(items_subquery.values('cbenef__code')[:1]),
            piscofins_cst_base=Subquery(items_subquery.values('piscofins_cst_code')[:1]),
            pis_aliquota_base=Subquery(items_subquery.values('pis_aliquota')[:1]),
            cofins_aliquota_base=Subquery(items_subquery.values('cofins_aliquota')[:1]),
            naturezareceita_base=Subquery(items_subquery.values('naturezareceita__code')[:1]), 
            type_product=Subquery(items_subquery.values('type_product')[:1]),       
        ).annotate(
            description_cliente=F('description')
        ).filter(
            ~Q(description_base=F('description_cliente'))
        ).order_by('description', 'origem')       
        
        # Reorganizar e renomear colunas adicionando sufixo _cliente, exceto para 'code' e 'client__name'
        combined_queryset = combined_queryset.values(
            'client__name',
            'code',
            'barcode_base',
            'barcode',
            'description_base',
            'description',
            'ncm_base',
            'ncm',
            'cest_base',
            'cest',
            'cfop_base',
            'cfop',
            'icms_cst_base',
            'icms_cst',
            'icms_aliquota_base',
            'icms_aliquota',
            'icms_aliquota_reduzida_base',
            'icms_aliquota_reduzida',
            'protege_base',
            'protege',
            'cbenef_base',
            'cbenef',
            'piscofins_cst_base',
            'piscofins_cst',
            'pis_aliquota_base',
            'pis_aliquota',
            'cofins_aliquota_base',
            'cofins_aliquota',
            'naturezareceita_base',
            'naturezareceita',
            'type_product'
        )
        
        # Salva o total de itens no queryset combinado
        self.total_items = combined_queryset.count()        

        return [
            {
                **{key + '_cliente' if '_base' not in key and key not in ['code', 'client__name'] else key: value 
                for key, value in item.items()}
            }
            for item in combined_queryset
        ]  
    
   
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        client = get_object_or_404(Client, id=self.kwargs.get('client_id'))
        context['client'] = client
        context['client_name'] = client.name
        context['client_id'] = client.id
        context['filter_params'] = self.request.GET
        context['total_items'] = self.total_items
        icms_cst_choices = list(IcmsCst.objects.values_list('code', 'code'))  
        cfop_choices = list(Cfop.objects.values_list('cfop', 'description'))
        # Adicionando cbenef ao contexto
        context['cbenef_choices'] = CBENEF.objects.all()         
        context['icms_cst_choices'] = icms_cst_choices        
        context['cfop_choices'] = cfop_choices
        context['protege_choices'] = Protege.objects.all()
        context['piscofins_choices'] = PisCofinsCst.objects.all()
        context['naturezareceita_choices'] = NaturezaReceita.objects.all()
        context['icmsaliquota_choices'] = IcmsAliquota.objects.all()
        icmsaliquotareduzida_codes = IcmsAliquotaReduzida.objects.values_list('code', flat=True)
        context['icmsaliquotareduzida_codes'] = set(icmsaliquotareduzida_codes)
        context['form'] = ImportedItemForm()
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

class XLSXUploadDivergentView(View):
    template_name = 'upload_items.html'
    logger = logging.getLogger(__name__)  # Configurar o logger
    
    TYPE_PRODUCT_CHOICES = {
        'Revenda': 'Revenda',
        'Imobilizado': 'Imobilizado',
        'Insumos': 'Insumos',
    }   
    
    REQUIRED_COLUMNS = [
        'codigo', 'barcode', 'description', 'ncm', 'cest', 'cfop', 'icms_cst', 
        'icms_aliquota', 'icms_aliquota_reduzida', 'piscofins_cst', 'naturezareceita', 
        'protege', 'cbenef', 'tipo_produto', 'outros_detalhes'
    ]     

    def post(self, request, client_id):
        print('Divergentes');
        start_time = time.time()
        client = get_object_or_404(Client, id=client_id)
        form = CSVUploadForm(request.POST, request.FILES)
        if form.is_valid():
            xlsx_file = request.FILES['csv_file']
            try:
                df = pd.read_excel(xlsx_file, dtype={
                    'ncm_base': str, 
                    'cest_base': str, 
                    'barcode_base': str, 
                    'naturezareceita_base': str,
                    'tipo_produto': str,  # Adicionar tipo_produto
                })
                
                
                # 1. Remover colunas específicas
                columns_to_remove = [col for col in df.columns if col.endswith('_cliente')]
                columns_to_remove.append('client__name')  # Adicionando client__name à lista de colunas para remover
                df = df.drop(columns=columns_to_remove)

                # 2. Renomear colunas
                rename_mapping = {
                    'code': 'codigo'
                }
                df = df.rename(columns=lambda x: x.replace('_base', '').replace('_cliente', '') if x not in rename_mapping else rename_mapping[x])

                print(df.columns)
                # Verificação das colunas obrigatórias
                missing_columns = [col for col in self.REQUIRED_COLUMNS if col not in df.columns]
                if missing_columns:
                    end_time = time.time()
                    elapsed_time = round(end_time - start_time, 3)
                     
                    error_message = [f"Erro: As seguintes colunas estão faltando no arquivo Excel: {', '.join(missing_columns)}"]
                    self.logger.error(error_message)
                    # return JsonResponse({'error': error_message}, status=400)
                    return JsonResponse({
                        'message': 'Colunas faltantes.',
                        'errors': error_message,
                        'elapsed_time': elapsed_time
                    }, status=400)                 
                
                
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
                
                # Adicionando a transformação e validação de tipo_produto
                df['tipo_produto'] = df['tipo_produto'].str.capitalize().str.strip()
                valid_tipo_produto = set(self.TYPE_PRODUCT_CHOICES.keys())
                invalid_tipo_produto = df[~df['tipo_produto'].isin(valid_tipo_produto)]

                if not invalid_tipo_produto.empty:
                    invalid_details = [
                        f"Erro na linha {index + 2} [tipo_produto]: {row['tipo_produto']} é um valor inválido."
                        for index, row in invalid_tipo_produto.iterrows()
                    ]
                    end_time = time.time()
                    elapsed_time = round(end_time - start_time, 3)
                    return JsonResponse({
                        'message': 'Linhas inválidas encontradas.',
                        'errors': invalid_details,
                        'elapsed_time': elapsed_time
                    }, status=400)                

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

                batch_size = 1000
                
                print(df)

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
                                'type_product': self.TYPE_PRODUCT_CHOICES[row['tipo_produto']], 
                                'other_information': row['outros_detalhes'],
                                'is_active': True,
                                'is_pending_sync': True,
                                'updated_at': current_time,
                                'await_sync_at': current_time,
                                'user_updated': user,
                                'status_item': 1,
                            }

                            if str(row['codigo']) in existing_items:
                                item = existing_items[str(row['codigo'])]  # Converter para string
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
                        with transaction.atomic():
                            # Atualiza os itens em Item
                            for i in range(0, len(items_to_update), batch_size):
                                batch = items_to_update[i:i + batch_size]
                                Item.objects.bulk_update(batch, fields=[
                                    'barcode', 'description', 'ncm', 'cest', 'cfop_id', 'icms_cst_id', 
                                    'icms_aliquota_id', 'icms_aliquota_reduzida', 'protege_id', 'cbenef_id', 
                                    'piscofins_cst', 'pis_aliquota', 'cofins_aliquota', 'naturezareceita_id', 
                                    'type_product', 'other_information',
                                    'is_active', 'is_pending_sync', 'updated_at', 'user_updated'
                                ])

                            # Atualiza os itens correspondentes em ImportedItem
                            imported_items_to_update = ImportedItem.objects.filter(
                                client=client,
                                code__in=[item.code for item in items_to_update]  
                            )
                            imported_items_to_update.update(is_pending=False)                        

                    # if items_to_update:
                    #     for i in range(0, len(items_to_update), batch_size):
                    #         batch = items_to_update[i:i + batch_size]
                    #         Item.objects.bulk_update(batch, fields=[
                    #             'barcode', 'description', 'ncm', 'cest', 'cfop_id', 'icms_cst_id', 
                    #             'icms_aliquota_id', 'icms_aliquota_reduzida', 'protege_id', 'cbenef_id', 
                    #             'piscofins_cst', 'pis_aliquota', 'cofins_aliquota', 'naturezareceita_id', 
                    #             'type_product', 'other_information',
                    #             'is_active', 'is_pending_sync', 'updated_at', 'user_updated'
                    #         ])

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

            end_time = time.time()
            elapsed_time = round(end_time - start_time, 3)

            return JsonResponse({
                'message': 'Todos os itens foram salvos/atualizados com sucesso!',
                'processed_rows': len(df),
                'elapsed_time': elapsed_time
            })

        self.logger.error(f"Form inválido: {form.errors}")
        return JsonResponse({'errors': form.errors}, status=400)