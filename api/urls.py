from django.urls import path
from . import views
from api.viewapiteste import ImportItemTestingView, ClientItemTestingView, ClientOneItemTestingView

urlpatterns = [
    path('enviar/', views.ImportItemView.as_view(), name='items-imported-client-view'),
    path('receber/', views.ClientItemView.as_view(), name='items-client-view'),
    path('consultar/<str:code>', views.ClientOneItemView.as_view(), name='items-client-view-code'),   
    
    path('test/enviar/', ImportItemTestingView.as_view(), name='test-items-imported-client-view'),
    path('test/receber/', ClientItemTestingView.as_view(), name='test-items-client-view'),    
    path('test/consultar/<str:code>', ClientOneItemTestingView.as_view(), name='test-items-client-view-code'),   
]

