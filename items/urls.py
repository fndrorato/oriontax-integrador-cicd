from django.urls import path
from .views import (
    get_item_logs,
    export_items_to_excel,
    download_file,
    validate_item,
    save_imported_item,
    save_bulk_imported_item,
    inactive_items_item_awaiting,
    ItemListView,
    ItemCreateView,
    ItemUpdateView,
    XLSXUploadView,
    ImportedItemListViewNewItem,
    ImportedItemListViewAwaitSyncItem,
    ImportedItemListViewDivergentItemExcelVersion,
    ImportedItemListViewDivergentDescriptionItemExcelVersion,
    XLSXUploadDivergentView,
    ImportedItemListViewInactiveItem
)

urlpatterns = [
    path('logs/<str:model_name>/<int:object_id>/', get_item_logs, name='get_item_logs'),
    path('download/<str:filename>/', download_file, name='download_file'),
    path('clientes/items/export/<int:client_id>/<str:table>/', export_items_to_excel, name='export_items_to_excel'),
    path('validate-item/', validate_item, name='validate_code_item'),
    path('clientes/items/<int:client_id>/', ItemListView.as_view(), name='item_list'),
    path('clientes/items/<int:client_id>/create/', ItemCreateView.as_view(), name='item_create'),
    path('clientes/items/<int:client_id>/<int:pk>/update/', ItemUpdateView.as_view(), name='item_update'),
    path('clientes/items/<int:client_id>/upload/', XLSXUploadView.as_view(), name='items_upload'),
    
    path('clientes/items-pendentes-novos/<int:client_id>/', ImportedItemListViewNewItem.as_view(), name='imported_item_list'),    
    path('clientes/items-inativos/<int:client_id>/', ImportedItemListViewInactiveItem.as_view(), name='inactive_item_list'),
    path('clientes/items-aguardando-validacao/<int:client_id>/', ImportedItemListViewAwaitSyncItem.as_view(), name='awaiting_item_list'),
    path('clientes/items-pendentes-divergentes/<int:client_id>/', ImportedItemListViewDivergentItemExcelVersion.as_view(), name='imported_divergent_item_list'),    
    path('clientes/items-pendentes-descricao/<int:client_id>/', ImportedItemListViewDivergentDescriptionItemExcelVersion.as_view(), name='imported_descricao_item_list'),        
    path('clientes/items-pendentes/save-imported-item/', save_bulk_imported_item, name='save_imported_item'),
    path('clientes/items-pendentes/inactive-items/', inactive_items_item_awaiting, name='inactive_items_item_awaiting'),
    path('clientes/items-pendentes/<int:client_id>/upload/', XLSXUploadDivergentView.as_view(), name='items_divergent_upload'),
]