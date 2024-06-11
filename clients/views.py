from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.contrib.auth.models import User, Group
from erp.models import ERP
from .models import Client, Store, Cities
from .forms import ClientForm, StoreForm
from django.urls import reverse_lazy
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.views import View
from django.views.generic import ListView, CreateView, TemplateView, UpdateView, DeleteView, DetailView

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
        return Client.objects.all()

@method_decorator(login_required(login_url='login'), name='dispatch')
class NewClientCreateView(CreateView):
    model = Client
    form_class = ClientForm
    template_name = 'create_client.html'
    success_url = '/clientes/'
    
    def form_invalid(self, form):
        print("Form is invalid")
        print("POST data:", self.request.POST)
        print("Form errors:", form.errors)
        return super().form_invalid(form)    
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['erps'] = ERP.objects.all()
        analysts_group = Group.objects.get(name='analista')
        context['users'] = User.objects.filter(groups=analysts_group)  
        
        return context  
    
@method_decorator(login_required(login_url='login'), name='dispatch')
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
        
        # Obtenha as stores associadas ao cliente
        stores = Store.objects.filter(client_id=client_id)
        context['stores'] = stores

        # Adicione o form para adicionar uma nova store
        context['store_form'] = StoreForm() 
        return context      

    def get_success_url(self):
        return reverse_lazy('client_update', kwargs={'pk': self.object.pk})     

@method_decorator(login_required(login_url='login'), name='dispatch')
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
class StoreUpdateView(UpdateView):
    model = Store
    form_class = StoreForm

    def form_valid(self, form):
        self.object = form.save()
        return JsonResponse({'success': True})

    def form_invalid(self, form):
        return JsonResponse({'success': False, 'errors': form.errors})       
        
@method_decorator(login_required(login_url='login'), name='dispatch')
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
                