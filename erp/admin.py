from django.contrib import admin
from erp.models import ERP, AccessDropbox, ERPIntegrationSchedule

@admin.register(ERP)
class ERPModelAdmin(admin.ModelAdmin):
    list_display = ('name', 'description', 'method_integration', 'periodicity',)
    
@admin.register(AccessDropbox)
class AccessDropboxModelAdmin(admin.ModelAdmin):
    list_display = ('client_id', 'access_token', 'refresh_token', 'created_at', 'updated_at',) 
    search_fields = ('client_id', 'access_token')  # Campos que podem ser pesquisados
    readonly_fields = ('created_at', 'updated_at')  # Campos que serão apenas leitura

@admin.register(ERPIntegrationSchedule)
class ERPIntegrationScheduleAdmin(admin.ModelAdmin):
    list_display = ('description',)
