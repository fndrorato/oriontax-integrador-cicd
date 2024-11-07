from django.urls import path
from . import views
from api.viewapiteste import ImportItemTestingView, ClientItemTestingView, ClientOneItemTestingView
from api.view_user import LoginView
from api.view_import import UploadZipView

urlpatterns = [
    path('enviar/', views.ImportItemView.as_view(), name='items-imported-client-view'),
    path('receber/', views.ClientItemView.as_view(), name='items-client-view'),
    path('consultar/<str:code>', views.ClientOneItemView.as_view(), name='items-client-view-code'),   
    
    path('test/enviar/', ImportItemTestingView.as_view(), name='test-items-imported-client-view'),
    path('test/receber/', ClientItemTestingView.as_view(), name='test-items-client-view'),    
    path('test/consultar/<str:code>', ClientOneItemTestingView.as_view(), name='test-items-client-view-code'),   
    
    path('login/', LoginView.as_view(), name='api-login'),
    # Recebe o arquivo que será enviado através do extrator do XML
    path('upload-zip/', UploadZipView.as_view(), name='upload-zip'),    
]

