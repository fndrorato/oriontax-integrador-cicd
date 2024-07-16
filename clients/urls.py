# URL relacionandas aos clientes
from django.urls import path
from . import views

urlpatterns = [
    path('clientes/', views.ClientListView.as_view(), name='clients_list'),
    path('clientes/novo-cliente/', views.NewClientCreateView.as_view(), name='client_create'),
    path('clientes/<int:pk>/update/', views.ClientUpdateView.as_view(), name='client_update'),     
    path('clientes/<int:client_id>/store/', views.StoreCreateView.as_view(), name='store_create'),  
    path('clientes/<int:client_id>/store/<int:pk>/update/', views.StoreUpdateView.as_view(), name='store_update'),      
    path('clientes/<int:client_id>/store/detail/<int:pk>/', views.StoreDetailView.as_view(), name='store_detail'),
    path('clientes/<int:client_id>/store/delete/<int:pk>/', views.StoreDeleteView.as_view(), name='store_delete'),
    
    path('clientes/validador-integracao/', views.XLSXSimulateValidateItems.as_view(), name='validate_simulate'),
    path('clientes/executar-sincronizacao/<int:client_id>/', views.RunSelectView.as_view(), name='run_select'),    
    path('clientes/executar-atualizacoes/<int:client_id>/', views.RunUpdateView.as_view(), name='run_update'),    
]
