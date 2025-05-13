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
    path('process-xml/', views.ProcessZipView.as_view(), name='upload-zip-xml'),
    path('process-sped/', views.ProcessSPED.as_view(), name='upload-zip-sped'),
    path('generate-group-csv/<str:code>', views.GenerateCSVGroup.as_view(), name='generate-reg0000-csv'),
    path('generate-detail-csv/<str:code>', views.GenerateCSVDetail.as_view(), name='generate-reg0000d-csv'),
    path('save-xml-sped/', views.SaveFilesDefinitely.as_view(), name='save-xml-sped'),
    
    
]

