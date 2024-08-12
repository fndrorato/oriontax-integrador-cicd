from django.urls import path
from . import views


urlpatterns = [
    path('enviar/', views.ImportItemView.as_view(), name='items-imported-client-view'),
    path('receber/', views.ClientItemView.as_view(), name='items-client-view'),
    path('consultar/<str:code>', views.ClientOneItemView.as_view(), name='items-client-view-code'),   
]

