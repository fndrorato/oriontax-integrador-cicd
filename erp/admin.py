from django.contrib import admin
from .models import ERP, AccessDropbox

@admin.register(ERP)
class ERPModelAdmin(admin.ModelAdmin):
    list_display = ('name', 'description')   
    
@admin.register(AccessDropbox)
class AccessDropboxModelAdmin(admin.ModelAdmin):
    list_display = ('client_id', 'access_token', 'refresh_token', 'created_at', 'updated_at')  # Campos a serem exibidos na lista
    search_fields = ('client_id', 'access_token')  # Campos que podem ser pesquisados
    readonly_fields = ('created_at', 'updated_at')  # Campos que serão apenas leitura

