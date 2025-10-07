from django.urls import path
from . import views
from api.viewapiteste import ImportItemTestingView, ClientItemTestingView, ClientOneItemTestingView
from api.view_user import LoginView
from api.view_import import UploadZipView

urlpatterns = [
    path('v1/enviar/', views.ImportItemView.as_view(), name='items-imported-client-view'),
    path('v1/receber/', views.ClientItemView.as_view(), name='items-client-view'),
    path('v1/consultar/<str:code>', views.ClientOneItemView.as_view(), name='items-client-view-code'),
    
    path('v2/enviar/', views.ImportItemV2View.as_view(), name='items-imported-client-view-v2'),
    path('v2/receber/', views.ClientItemV2View.as_view(), name='items-client-view-v2'),
    
    path('test/enviar/', ImportItemTestingView.as_view(), name='test-items-imported-client-view'),
    path('test/receber/', ClientItemTestingView.as_view(), name='test-items-client-view'),    
    path('test/consultar/<str:code>', ClientOneItemTestingView.as_view(), name='test-items-client-view-code'),   
    
    path('v1/login/', LoginView.as_view(), name='api-login'),
    # Recebe o arquivo que será enviado através do extrator do XML
    path('v1/upload-zip/', UploadZipView.as_view(), name='upload-zip'),
    path('v1/process-xml/', views.ProcessZipView.as_view(), name='upload-zip-xml'),
    path('v1/process-sped/', views.ProcessSPED.as_view(), name='upload-zip-sped'),
    path('v1/generate-group-csv/<str:code>', views.GenerateCSVGroup.as_view(), name='generate-reg0000-csv'),
    path('v1/generate-detail-csv/<str:code>', views.GenerateCSVDetail.as_view(), name='generate-reg0000d-csv'),
    path('v1/save-xml-sped/', views.SaveFilesDefinitely.as_view(), name='save-xml-sped'),
    
    
]

