from django.urls import path
from .views import export_items_to_excel, download_file, validate_item, ItemListView, ItemCreateView, ItemUpdateView, XLSXUploadView, XLSXUploadViewV2

urlpatterns = [
    path('download/<str:filename>/', download_file, name='download_file'),
    path('clientes/items/export/<int:client_id>/', export_items_to_excel, name='export_items_to_excel'),
    path('validate-item/', validate_item, name='validate_code_item'),
    path('clientes/items/<int:client_id>/', ItemListView.as_view(), name='item_list'),
    path('clientes/items/<int:client_id>/create/', ItemCreateView.as_view(), name='item_create'),
    # path('clientes/store/items/<int:store_id>/<int:pk>/', ItemDetailView.as_view(), name='item_detail'),
    path('clientes/items/<int:client_id>/<int:pk>/update/', ItemUpdateView.as_view(), name='item_update'),
    # path('clientes/store/items/<int:store_id>/<int:pk>/delete/', ItemDeleteView.as_view(), name='item_delete'),
    path('clientes/items/<int:client_id>/upload/', XLSXUploadViewV2.as_view(), name='items_upload'),
]