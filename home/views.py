from django.urls import reverse
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from datetime import datetime, timezone
from django.utils.timesince import timesince
from django.views.generic import TemplateView, ListView
from django.core.paginator import Paginator  # Importando o Paginator
from django.db.models import Q, Value, CharField, F, Subquery, OuterRef
from django.db.models.functions import Concat, Cast
from clients.models import Client, Store
from items.models import Item, ImportedItem
from rolepermissions.decorators import has_role_decorator
from rolepermissions.checkers import has_role

@method_decorator(login_required(login_url='login'), name='dispatch')
class HomeView(TemplateView):
    template_name = 'home.html'

    def get_context_data(self, **kwargs):
        user = self.request.user        
        context = super().get_context_data(**kwargs)
        
        if has_role(user, 'analista'):
            clients = Client.objects.filter(user_id=user.id).order_by('name')
        else:
            clients = Client.objects.all().order_by('name')
            
        clients_with_item_count = []
        total_items = 0
        total_stores = 0
        total_imported_itens = 0

        for client in clients:
            item_count = Item.objects.filter(client=client).count()
            store_count = Store.objects.filter(client=client).count()
            
            imported_itens_count_news = ImportedItem.objects.filter(client=client, is_pending=True, status_item=0).count()
            
            # Subconsulta para encontrar os itens no modelo Item com client e code iguais e com status_item igual a 1 ou 2
            item_subquery = Item.objects.filter(
                client=OuterRef('client'),
                code=OuterRef('code'),
                status_item__in=[1, 2]
            ).values('code')

            imported_itens_count_diver = ImportedItem.objects.filter(
                client=client,
                is_pending=True,
                status_item=1
            ).exclude(
                divergent_columns__icontains="description"
            ).exclude(
                code__in=Subquery(item_subquery)
            ).count()        
            
            imported_itens_count_with_description = ImportedItem.objects.filter(
                client=client, 
                is_pending=True, 
                status_item=1,
                divergent_columns__icontains="description"
            ).exclude(
                code__in=Subquery(item_subquery)
            ).count()    
            
            itens_await_sync = Item.objects.filter(
                client=client
            ).filter(
                Q(status_item=1) | Q(status_item=2)
            ).count()    
            
            imported_itens_count = imported_itens_count_news + imported_itens_count_diver + imported_itens_count_with_description              
            
            total_imported_itens += imported_itens_count
            total_items += item_count
            total_stores += store_count
            clients_with_item_count.append({
                'client': client,
                'item_count': item_count,
                'store_count': store_count,
                'imported_itens_count': imported_itens_count,
                'produtos_novos_pendentes': imported_itens_count_news,
                'produtos_com_descricao_divergente': imported_itens_count_with_description,                
                'produtos_com_divergencia': imported_itens_count_diver,
                'produtos_aguardando_sync': itens_await_sync,
            })
        context['total_stores'] = total_stores
        
        if clients.count() > 0:
            context['media_items'] = round(total_items / clients.count(),1)
        else:
            context['media_items'] = 0
            
        context['clients'] = clients_with_item_count
        context['total_imported_itens'] = total_imported_itens
        return context

@method_decorator(login_required(login_url='login'), name='dispatch')
class SearchResultsView(ListView):
    model = None  # Não especificamos um modelo diretamente, pois vamos sobrescrever o método get_queryset()

    def get(self, request, *args, **kwargs):
        query = request.GET.get('q')
        if query:
            # Execute a pesquisa em diferentes modelos
            results_client = Client.objects.filter(
                (Q(accounting__name__icontains=query) | Q(name__icontains=query)) & ~Q(id=4)
            ).select_related('user').annotate(
                result_type=Value('Cliente', output_field=CharField()),
                display_name=F('name'),
                extra_info=Concat('user__first_name', Value(' '), 'user__last_name', output_field=CharField()),
                last_updated=F('updated_at')
            )        
            
            results_store = Store.objects.filter(
                (Q(corporate_name__icontains=query) | Q(city__nome__icontains=query)) & ~Q(client_id=4)
            ).annotate(
                result_type=Value('Loja', output_field=CharField()),
                display_name=F('corporate_name'),
                extra_info=Value('', output_field=CharField()),
                last_updated=F('updated_at')
            )
            results_item = Item.objects.filter(
                (Q(description__icontains=query) | Q(barcode__icontains=query )) & ~Q(client_id=4) 
            ).select_related('client__user').annotate(
                result_type=Value('Produtos', output_field=CharField()),
                display_name=Concat(Cast(F('code'), CharField()), Value(' - '), F('description'), output_field=CharField()),
                extra_info=Concat(F('client__name'), Value(' - '), F('client__user__first_name'), Value(' '), F('client__user__last_name'), output_field=CharField()),
                last_updated=F('updated_at')
            )

            # Combine os resultados em uma lista única
            results = list(results_client) + list(results_store) + list(results_item)

            # Calcular o total de resultados encontrados
            total_results = len(results)

            # Paginação dos resultados
            paginator = Paginator(results, 10)  # 10 itens por página
            page_number = request.GET.get('page')
            page_obj = paginator.get_page(page_number)

            # Criar links para cada resultado
            for result in page_obj:
                if result.result_type == 'Cliente':
                    result.url = reverse('client_update', args=[result.pk])
                elif result.result_type == 'Loja':
                    result.url = reverse('store_update', args=[result.pk])
                elif result.result_type == 'Produtos':
                    result.url = reverse('item_update', args=[result.client.pk, result.pk])

                # Calcular tempo desde a última atualização
                if result.last_updated:
                    result.time_since_updated = self.get_time_since_updated(result.last_updated)

            context = {
                'results': page_obj,
                'query': query,
                'total_results': total_results,
            }
            return render(request, 'search_results.html', context)
        else:
            return render(request, 'search_results.html', {'query': query})

    def get_time_since_updated(self, updated_at):
        """
        Retorna uma string formatada indicando quanto tempo atrás a atualização ocorreu.
        """
        now = datetime.now(timezone.utc)
        delta = now - updated_at
        return timesince(updated_at, now=now).split(", ")[0]

        