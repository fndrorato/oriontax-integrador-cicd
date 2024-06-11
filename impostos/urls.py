# URL relacionandas aos usuários
from django.urls import path
from . import views

urlpatterns = [
    path('impostos/cfop/', views.CfopsListView.as_view(), name='cfop_list'),
    path('impostos/cfop/new/', views.CfopCreateView.as_view(), name='cfop_create'),
    path('impostos/cfop/detail/<int:pk>', views.CfopDetailView.as_view(), name='cfop_detail'),    
    path('impostos/cfop/<int:pk>/update/', views.CfopUpdateView.as_view(), name='cfop_update'), 
    path('impostos/cfop/delete/<int:pk>', views.CfopDeleteView.as_view(), name='cfop_delete'), 
    
    path('impostos/cst-icms/', views.IcmsCstListView.as_view(), name='icmscst_list'),
    path('impostos/cst-icms/new/', views.IcmsCstCreateView.as_view(), name='icmscst_create'),
    path('impostos/cst-icms/detail/<int:pk>', views.IcmsCstDetailView.as_view(), name='icmscst_detail'),    
    path('impostos/cst-icms/<int:pk>/update/', views.IcmsCstUpdateView.as_view(), name='icmscst_update'), 
    path('impostos/cst-icms/delete/<int:pk>', views.IcmsCstDeleteView.as_view(), name='icmscst_delete'), 
    
    path('impostos/icms-aliquota/', views.IcmsAliquotaListView.as_view(), name='icmsaliquota_list'),
    path('impostos/icms-aliquota/new/', views.IcmsAliquotaCreateView.as_view(), name='icmsaliquota_create'),
    path('impostos/icms-aliquota/detail/<int:pk>', views.IcmsAliquotaDetailView.as_view(), name='icmsaliquota_detail'),    
    path('impostos/icms-aliquota/<int:pk>/update/', views.IcmsAliquotaUpdateView.as_view(), name='icmsaliquota_update'), 
    path('impostos/icms-aliquota/delete/<int:pk>', views.IcmsAliquotaDeleteView.as_view(), name='icmsaliquota_delete'), 
    
    path('impostos/icms-aliquota-reduzida/', views.IcmsAliquotaReduzidaListView.as_view(), name='icmsaliquotareduzida_list'),
    path('impostos/icms-aliquota-reduzida/new/', views.IcmsAliquotaReduzidaCreateView.as_view(), name='icmsaliquotareduzida_create'),
    path('impostos/icms-aliquota-reduzida/detail/<int:pk>', views.IcmsAliquotaReduzidaDetailView.as_view(), name='icmsaliquotareduzida_detail'),    
    path('impostos/icms-aliquota-reduzida/<int:pk>/update/', views.IcmsAliquotaReduzidaUpdateView.as_view(), name='icmsaliquotareduzida_update'), 
    path('impostos/icms-aliquota-reduzida/delete/<int:pk>', views.IcmsAliquotaReduzidaDeleteView.as_view(), name='icmsaliquotareduzida_delete'),
    
    path('impostos/cbenef/', views.CbenefListView.as_view(), name='cbenef_list'),
    path('impostos/cbenef/new/', views.CbenefCreateView.as_view(), name='cbenef_create'),
    path('impostos/cbenef/detail/<str:pk>', views.CbenefDetailView.as_view(), name='cbenef_detail'),    
    path('impostos/cbenef/<str:pk>/update/', views.CbenefUpdateView.as_view(), name='cbenef_update'), 
    path('impostos/cbenef/delete/<str:pk>', views.CbenefDeleteView.as_view(), name='cbenef_delete'),
    
    path('impostos/protege/', views.ProtegeListView.as_view(), name='protege_list'),
    path('impostos/protege/new/', views.ProtegeCreateView.as_view(), name='protege_create'),
    path('impostos/protege/detail/<int:pk>', views.ProtegeDetailView.as_view(), name='protege_detail'),    
    path('impostos/protege/<int:pk>/update/', views.ProtegeUpdateView.as_view(), name='protege_update'), 
    path('impostos/protege/delete/<int:pk>', views.ProtegeDeleteView.as_view(), name='protege_delete'),    
    
    path('impostos/pis-cofins-cst/', views.PisCofinsCstListView.as_view(), name='piscofinscst_list'),
    path('impostos/pis-cofins-cst/new/', views.PisCofinsCstCreateView.as_view(), name='piscofinscst_create'),
    path('impostos/pis-cofins-cst/detail/<str:pk>', views.PisCofinsCstDetailView.as_view(), name='piscofinscst_detail'),    
    path('impostos/pis-cofins-cst/<str:pk>/update/', views.PisCofinsCstUpdateView.as_view(), name='piscofinscst_update'), 
    path('impostos/pis-cofins-cst/delete/<str:pk>', views.PisCofinsCstDeleteView.as_view(), name='piscofinscst_delete'),
    
    path('impostos/natureza-receita/', views.NaturezaReceitaListView.as_view(), name='naturezareceita_list'),
    path('impostos/natureza-receita/new/', views.NaturezaReceitaCreateView.as_view(), name='naturezareceita_create'),
    path('impostos/natureza-receita/detail/<int:pk>/', views.NaturezaReceitaDetailView.as_view(), name='naturezareceita_detail'),
    path('impostos/natureza-receita/<int:pk>/update/', views.NaturezaReceitaUpdateView.as_view(), name='naturezareceita_update'),
    path('impostos/natureza-receita/delete/<int:pk>', views.NaturezaReceitaDeleteView.as_view(), name='naturezareceita_delete'),    
    
    path('get-piscofins-aliquota/', views.get_piscofins_aliquota, name='get_piscofins_aliquota'),
    
]
