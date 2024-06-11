# URL relacionandas aos usuários
from django.urls import path
from . import views

urlpatterns = [
    path('contabilidades/', views.AccountingsListView.as_view(), name='accountings_list'),
    path('contabilidades/novacontabilidade/', views.NewAccountingCreateView.as_view(), name='create_accounting'),
    path('contabilidades/<int:pk>/update/', views.AccountingUpdateView.as_view(), name='update_accounting'), 
    # path('sistemas/<int:pk>/delete/', views.ErpDeleteView.as_view(), name='erp_delete'),
]
