from django.urls import path
from . import views

urlpatterns = [
    path('notifications/', views.notificacoes_json, name='notificacoes_json'),
    path('notifications/read/<int:pk>/', views.marcar_notificacao_como_lida, name='notificacao_read'),
    path('notifications/read/all/', views.marcar_todas_como_lidas, name='notificacoes_marcar_todas'),   
]
