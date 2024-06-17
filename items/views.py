import csv
import io
import os
import time
import pandas as pd
from django.conf import settings
from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse, FileResponse, HttpResponseNotFound, HttpResponse
from django.utils import timezone
from django.core.exceptions import ValidationError, ObjectDoesNotExist
from django.contrib import messages
from django.urls import reverse_lazy
from django.db import transaction
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
import logging


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
    
    def get_success_url(self):
        return reverse_lazy('item_update', kwargs={'pk': self.object.pk, 'client_id': self.object.client_id})          

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


class XLSXUploadViewV1(View):
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
        start_time = time.time()
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

            # Cache de Consultas
            cfop_cache = {str(cfop.cfop): cfop for cfop in Cfop.objects.all()}
            icms_cst_cache = {str(cst.code): cst for cst in IcmsCst.objects.all()}
            icms_aliquota_cache = {str(aliquota.code): aliquota for aliquota in IcmsAliquota.objects.all()}
            piscofins_cst_cache = {str(cst.code): cst for cst in PisCofinsCst.objects.all()}
            natureza_receita_cache = {str(nr.code): nr for nr in NaturezaReceita.objects.all()}
            protege_cache = {str(protege.code): protege for protege in Protege.objects.all()}
            cbenef_cache = {str(cbenef.code): cbenef for cbenef in CBENEF.objects.all()}

            row_number = 2  # Começa com 2 para pular o cabeçalho

            for row in sheet.iter_rows(min_row=2, values_only=True):  # Pulando a primeira linha (cabeçalho)
                try:
                    piscofins_cst_code = str(row[11])
                    if len(piscofins_cst_code) == 1:
                        piscofins_cst_code = f"0{piscofins_cst_code}"

                    # Validar e buscar/instanciar campos relacionados
                    cfop = cfop_cache.get(str(row[5]))
                    if not cfop:
                        raise ValueError(f"Código CFOP não encontrado: {row[5]}")

                    icms_cst = icms_cst_cache.get(str(row[6]))
                    if not icms_cst:
                        raise ValueError(f"Código ICMS CST não encontrado: {row[6]}")

                    icms_aliquota = icms_aliquota_cache.get(str(row[7]))
                    if not icms_aliquota:
                        raise ValueError(f"Código ICMS Alíquota não encontrado: {row[7]}")

                    icms_aliquota_reduzida = icms_aliquota_cache.get(str(row[8]))
                    if not icms_aliquota_reduzida:
                        raise ValueError(f"Código ICMS Alíquota Reduzida não encontrado: {row[8]}")

                    piscofins_cst = piscofins_cst_cache.get(piscofins_cst_code)
                    if not piscofins_cst:
                        raise ValueError(f"Código PIS/COFINS CST não encontrado: {piscofins_cst_code}")

                    natureza_receita = natureza_receita_cache.get(str(row[14])) if row[14] else None
                    if row[14] and not natureza_receita:
                        raise ValueError(f"Código Natureza Receita não encontrado: {row[14]}")

                    protege = protege_cache.get(str(row[9])) if row[9] else None
                    if row[9] and not protege:
                        raise ValueError(f"Código Protege não encontrado: {row[9]}")

                    cbenef = cbenef_cache.get(str(row[10])) if row[10] else None
                    if row[10] and not cbenef:
                        raise ValueError(f"Código CBENEF não encontrado: {row[10]}")

                    item_data = {
                        'client': client,
                        'code': row[0],
                        'barcode': row[1],
                        'description': row[2],
                        'ncm': row[3],
                        'cest': row[4],
                        'cfop': cfop,
                        'icms_cst': icms_cst,
                        'icms_aliquota': icms_aliquota,
                        'icms_aliquota_reduzida': icms_aliquota_reduzida,
                        'protege': protege,
                        'cbenef': cbenef,
                        'piscofins_cst': piscofins_cst,
                        'pis_aliquota': piscofins_cst.pis_aliquota,
                        'cofins_aliquota': piscofins_cst.cofins_aliquota,
                        'naturezareceita': natureza_receita,
                        'is_active': True,
                        'is_pending_sync': True,
                        'updated_at': current_time,
                        'user_updated': user,
                    }

                    try:
                        item = Item.objects.get(client=client, code=row[0])
                        for key, value in item_data.items():
                            setattr(item, key, value)
                        items.append(item)
                    except Item.DoesNotExist:
                        items.append(Item(**item_data))

                except (KeyError, ValueError) as e:
                    errors.append(f"Erro na linha {row_number}: {str(e)}")

                row_number += 1  # Incrementa o contador de linha

            end_time = time.time()
            elapsed_time = round(end_time - start_time, 3)

            if errors:
                return JsonResponse({
                    'errors': errors,
                    'processed_rows': row_number - 2,
                    'elapsed_time': elapsed_time
                }, status=400)
            else:
                # Salvar todos os itens
                Item.objects.bulk_create(items, ignore_conflicts=True)
                return JsonResponse({
                    'message': 'Todos os itens foram salvos/atualizados com sucesso!',
                    'processed_rows': row_number - 2,
                    'elapsed_time': elapsed_time
                })

        print(f"Form inválido: {form.errors}")
        return JsonResponse({'errors': form.errors}, status=400)
    
class XLSXUploadViewV2(View):
    template_name = 'upload_items.html'

    def get(self, request, client_id):
        client = get_object_or_404(Client, id=client_id)
        form = CSVUploadForm()
        context = {
            'form': form,
            'client': client,
        }
        return render(request, self.template_name, context)

    logger = logging.getLogger(__name__)  # Configurar o logger

    @transaction.atomic  # Garante a atomicidade da transação
    def post(self, request, client_id):
        start_time = time.time()
        client = get_object_or_404(Client, id=client_id)
        form = CSVUploadForm(request.POST, request.FILES)
        if form.is_valid():
            xlsx_file = request.FILES['csv_file']
            df = pd.read_excel(xlsx_file)
            
            # Pré-validar códigos
            valid_cfops = set(Cfop.objects.values_list('cfop', flat=True))
            valid_icms_csts = set(IcmsCst.objects.values_list('code', flat=True))
            valid_icms_aliquotas = set(IcmsAliquota.objects.values_list('code', flat=True))
            valid_piscofins_csts = set(PisCofinsCst.objects.values_list('code', flat=True))
            valid_natureza_receitas = set(NaturezaReceita.objects.values_list('code', flat=True))
            valid_proteges = set(Protege.objects.values_list('code', flat=True))
            valid_cbenefs = set(CBENEF.objects.values_list('code', flat=True))
            
            # Adicionar a possibilidade de ser vazio/em branco
            valid_natureza_receitas.add(None)
            valid_cbenefs.add(None)
            
            # Carregar os dados de PisCofinsCst e NaturezaReceita em DataFrames
            piscofins_cst_df = pd.DataFrame(list(PisCofinsCst.objects.values('code', 'pis_aliquota', 'cofins_aliquota')))
            natureza_receita_df = pd.DataFrame(list(NaturezaReceita.objects.values('code', 'id', 'piscofins_cst_id')))

            # Converter os DataFrames para dicionários para consulta eficiente
            pis_cofins_cst_dict = piscofins_cst_df.set_index('code').to_dict('index')
            natureza_receita_dict = natureza_receita_df.set_index(['code', 'piscofins_cst_id']).to_dict('index')
            
            # Função para buscar IDs a partir dos códigos
            def get_natureza_receita_id(code, piscofins_cst_code):
                return natureza_receita_dict.get((code, piscofins_cst_code), {}).get('id')            

            # Convertendo os dados para strings e preenchendo zeros à esquerda quando necessário
            df['barcode'] = df['barcode'].fillna(0).astype(int).astype(str)
            df['ncm'] = df['ncm'].astype(str)
            df['cest'] = df['cest'].fillna(0).astype(int).astype(str)
            df['cfop'] = df['cfop'].astype(int)
            df['icms_cst'] = df['icms_cst'].astype(str)
            df['icms_aliquota'] = df['icms_aliquota'].astype(int)
            df['icms_aliquota_reduzida'] = df['icms_aliquota_reduzida'].astype(int)
            df['piscofins_cst'] = df['piscofins_cst'].astype(str).str.zfill(2)
            # df['naturezareceita'] = df['naturezareceita'].astype(str).replace('0', None)
            df['naturezareceita'] = df['naturezareceita'].fillna('').astype(str).str.zfill(3).replace(['000', 'nan'], None)
            df['protege'] = df['protege'].astype(int)
            df['cbenef'] = df['cbenef'].astype(str).replace('nan', None)
            # Truncar campos que excedem o tamanho máximo permitido
            df['description'] = df['description'].str[:255]
            df['cbenef'] = df['cbenef'].str[:8]
            

            # Lista para armazenar as linhas inválidas e seus motivos
            invalid_details = []

            # Função para verificar linhas inválidas
            def check_invalid_rows(df, column_name, valid_set):
                # Filtrar as linhas inválidas da coluna especificada, considerando valores não nulos e valores nulos
                invalid_rows = df[(~df[column_name].isin(valid_set)) & (~df[column_name].isnull())]
                
                for index, row in invalid_rows.iterrows():
                    error_message = f"Erro na linha[{column_name}] {index + 2}: {row[column_name]} é um valor inválido."
                    invalid_details.append(error_message)  # Adicionar o erro à lista                    
                return invalid_rows

            # Verificar cada coluna separadamente e parar se encontrar alguma linha inválida
            columns_to_check = [
                ('cfop', valid_cfops),
                ('icms_cst', valid_icms_csts),
                ('icms_aliquota', valid_icms_aliquotas),
                ('icms_aliquota_reduzida', valid_icms_aliquotas),
                ('piscofins_cst', valid_piscofins_csts),
                ('naturezareceita', valid_natureza_receitas),
                ('protege', valid_proteges),
                ('cbenef', valid_cbenefs)
            ]

            for column_name, valid_set in columns_to_check:
                invalid_rows = check_invalid_rows(df, column_name, valid_set)
                if not invalid_rows.empty:
                    break  # Interrompe o processo ao encontrar linhas inválidas

            if invalid_details:
                end_time = time.time()
                elapsed_time = round(end_time - start_time, 3)                 
                return JsonResponse({
                    'message': 'Linhas inválidas encontradas.',
                    'errors': invalid_details,
                    'elapsed_time': elapsed_time
                }, status=400)

            codigos = df['codigo'].tolist()  
            # Pré-carregar os itens existentes no banco de dados
            existing_items = {item.code: item for item in Item.objects.filter(client=client, code__in=df['codigo'])}

            
            # Busque todas as instâncias de PisCofinsCst de uma vez para eficiência
            pis_cofins_cst_instances = {obj.code: obj for obj in PisCofinsCst.objects.filter(code__in=df['piscofins_cst'])}
            
            items_to_create = []
            items_to_update = []
            user = request.user
            current_time = timezone.now()
            errors = []  # Lista para armazenar os erros
                                     
            #### ORIGINAL #####    
            for index, row in df.iterrows():
                try:
                    piscofins_cst_code = row['piscofins_cst']  # Garante que o código tenha 2 dígitos

                    # Obtenha a instância de PisCofinsCst correspondente
                    piscofins_cst = pis_cofins_cst_instances.get(piscofins_cst_code)
                    if not piscofins_cst:
                        raise ObjectDoesNotExist(f"PisCofinsCst com código {piscofins_cst_code} não encontrado")

                    pis_aliquota = piscofins_cst.pis_aliquota
                    cofins_aliquota = piscofins_cst.cofins_aliquota
                    
                    # Buscar o id de NaturezaReceita no DataFrame carregado
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
                        'cfop_id': row['cfop'],  # Verifique se o valor de 'cfop' é um número dentro do limite de 7 caracteres
                        'icms_cst_id': row['icms_cst'],
                        'icms_aliquota_id': row['icms_aliquota'],
                        'icms_aliquota_reduzida': row['icms_aliquota_reduzida'],
                        'protege_id': row['protege'],
                        'cbenef_id': row['cbenef'] if row['cbenef'] in valid_cbenefs else None,  # Verifique se o valor de 'cbenef' está dentro do limite de 8 caracteres
                        'piscofins_cst': piscofins_cst,
                        'pis_aliquota': pis_aliquota,
                        'cofins_aliquota': cofins_aliquota,
                        'naturezareceita_id': natureza_receita_id,
                        'is_active': True,
                        'is_pending_sync': True,
                        'updated_at': current_time,
                        'user_updated': user,
                    }

                    # Verificar se o item existe
                    if row['codigo'] in existing_items:
                        # Atualizar item existente
                        item = existing_items[row['codigo']]
                        for key, value in item_data.items():
                            setattr(item, key, value)
                        items_to_update.append(item)
                    else:
                        # Criar novo item
                        new_item = Item(**item_data)
                        items_to_create.append(new_item)

                except (ObjectDoesNotExist, ValidationError, TypeError, ValueError) as e:
                    error_message = f"Erro na linha {index + 2}: {e}"
                    self.logger.error(error_message)  # Log do erro para o servidor
                    errors.append(error_message)  # Adicionar o erro à lista
                    
            # Verificar se houve erros antes de prosseguir
            if errors:
                end_time = time.time()
                elapsed_time = round(end_time - start_time, 3)                
                return JsonResponse({
                    'message': 'Erros encontrados durante o processamento do arquivo.',
                    'errors': errors,
                    'elapsed_time': elapsed_time
                }, status=400)
                
            # Bulk create e bulk update
            Item.objects.bulk_create(items_to_create, ignore_conflicts=True)
            if items_to_update:
                Item.objects.bulk_update(items_to_update, fields=[
                    'barcode', 'description', 'ncm', 'cest', 'cfop', 'icms_cst', 
                    'icms_aliquota', 'icms_aliquota_reduzida', 'protege', 'cbenef', 
                    'piscofins_cst', 'pis_aliquota', 'cofins_aliquota', 'naturezareceita', 
                    'is_active', 'is_pending_sync', 'updated_at', 'user_updated'
                ])

            end_time = time.time()
            elapsed_time = round(end_time - start_time, 3)

            return JsonResponse({
                'message': 'Todos os itens foram salvos/atualizados com sucesso!',
                'processed_rows': len(df),
                'elapsed_time': elapsed_time
            })

        print(f"Form inválido: {form.errors}")
        return JsonResponse({'errors': form.errors}, status=400)

   