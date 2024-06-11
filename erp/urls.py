# URL relacionandas aos usuários
from django.urls import path
from . import views

urlpatterns = [
    path('sistemas/', views.ErpsListView.as_view(), name='erps_list'),
    path('sistemas/novosistema/', views.NewErpCreateView.as_view(), name='new_erp'),
    path('sistemas/<int:pk>/update/', views.ErpUpdateView.as_view(), name='erp_update'), 
    path('sistemas/<int:pk>/delete/', views.ErpDeleteView.as_view(), name='erp_delete'),
]
