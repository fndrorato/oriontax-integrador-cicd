from django.urls import path
from .views import (
    get_item_logs,
    export_items_to_excel,
    download_file,
    validate_item,
    save_imported_item,
    save_bulk_imported_item,
    ItemListView,
    ItemCreateView,
    ItemUpdateView,
    XLSXUploadView,
    ImportedItemListViewNewItem,
    ImportedItemListViewDivergentItem,
)

urlpatterns = [
    path('logs/<str:model_name>/<int:object_id>/', get_item_logs, name='get_item_logs'),
    path('download/<str:filename>/', download_file, name='download_file'),
    path('clientes/items/export/<int:client_id>/<str:table>/', export_items_to_excel, name='export_items_to_excel'),
    path('validate-item/', validate_item, name='validate_code_item'),
    path('clientes/items/<int:client_id>/', ItemListView.as_view(), name='item_list'),
    path('clientes/items/<int:client_id>/create/', ItemCreateView.as_view(), name='item_create'),
    # path('clientes/store/items/<int:store_id>/<int:pk>/', ItemDetailView.as_view(), name='item_detail'),
    path('clientes/items/<int:client_id>/<int:pk>/update/', ItemUpdateView.as_view(), name='item_update'),
    # path('clientes/store/items/<int:store_id>/<int:pk>/delete/', ItemDeleteView.as_view(), name='item_delete'),
    path('clientes/items/<int:client_id>/upload/', XLSXUploadView.as_view(), name='items_upload'),
    
    path('clientes/items-pendentes-novos/<int:client_id>/', ImportedItemListViewNewItem.as_view(), name='imported_item_list'),    
    path('clientes/items-pendentes-divergentes/<int:client_id>/', ImportedItemListViewDivergentItem.as_view(), name='imported_divergent_item_list'),    
    path('clientes/items-pendentes/save-imported-item/', save_bulk_imported_item, name='save_imported_item'),
]