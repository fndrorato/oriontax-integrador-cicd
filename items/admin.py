from django.contrib import admin
from .models import Item

class ItemAdmin(admin.ModelAdmin):
    list_display = ('client', 'code', 'barcode', 'description', 'ncm', 'cfop', 'icms_cst', 'piscofins_cst', 'is_active', 'is_pending_sync', 'created_at', 'updated_at', 'user_created', 'user_updated')
    list_filter = ('client', 'cfop', 'icms_cst', 'piscofins_cst', 'is_active', 'is_pending_sync')
    search_fields = ('client__name', 'barcode', 'description', 'ncm', 'code')


admin.site.register(Item, ItemAdmin)
