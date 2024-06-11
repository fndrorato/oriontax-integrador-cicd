import csv
import io
import os
from django.conf import settings
from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse, FileResponse, HttpResponseNotFound, HttpResponse
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.contrib import messages
from django.urls import reverse_lazy
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
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
                    print(f"Processando linha: {row}")
                    piscofins_cst_code = str(row[11])
                    if len(piscofins_cst_code) == 1:
                        piscofins_cst_code = f"0{piscofins_cst_code}"
                    piscofins_cst_code = str(piscofins_cst_code)                    
                    print(f"PisCofinsCst: {piscofins_cst_code}")
                    

                    
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
                    print(item_data)
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
