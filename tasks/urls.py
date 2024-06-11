# URL relacionandas aos usuários
from django.urls import path
from . import views

urlpatterns = [
    path('configuracoes/horario-execucao/', views.TaskCreateView.as_view(), name='task_create_execution_time'),
    path('configuracoes/horario-execucao/<int:pk>/update/', views.TaskUpdateView.as_view(), name='task_update_execution_time'), 
]
