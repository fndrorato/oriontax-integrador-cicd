from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.views.generic import TemplateView
from clients.models import Client, Store
from items.models import Item

@method_decorator(login_required(login_url='login'), name='dispatch')
class HomeView(TemplateView):
    template_name = 'home.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        clients = Client.objects.all()
        clients_with_item_count = []
        total_items = 0
        total_stores = 0

        for client in clients:
            item_count = Item.objects.filter(client=client).count()
            store_count = Store.objects.filter(client=client).count()
            total_items += item_count
            total_stores += store_count
            clients_with_item_count.append({
                'client': client,
                'item_count': item_count,
                'store_count': store_count
            })
        context['total_stores'] = total_stores
        context['media_items'] = total_items / clients.count()
        context['clients'] = clients_with_item_count
        return context
