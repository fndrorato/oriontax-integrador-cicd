from django.contrib import admin
from .models import Cities, Client, Store, LogIntegration, Syncing

@admin.register(Cities)
class CitiesAdmin(admin.ModelAdmin):
    list_display = ('nome', 'id_estado', 'ibge', 'nome_estado', 'uf_estado')
    search_fields = ('nome', 'ibge', 'nome_estado', 'uf_estado')
    
@admin.register(Store)
class StoreAdmin(admin.ModelAdmin):
    list_display = ('corporate_name', 'client', 'city', 'cnpj', 'is_active')
    search_fields = ('corporate_name', 'cnpj', 'client__name')    
    
@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):
    list_display = ('name', 'num_stores', 'date_contract', 'date_send', 'economic_benefit', 'erp', 'accounting', 'commercial_responsible', 'owner', 'email', 'contact', 'user', 'is_active', 'first_load_date', 'day_sent')
    search_fields = ('name', 'email', 'contact', 'owner')
    list_filter = ('date_contract', 'date_send', 'economic_benefit', 'erp')
    ordering = ('name',)

    fieldsets = (
        (None, {
            'fields': ('name', 'num_stores', 'date_contract', 'date_send', 'economic_benefit', 'erp', 'accounting', 'commercial_responsible', 'owner', 'email', 'contact', 'user', 'is_active', 'first_load_date', 'day_sent')
        }),
    )  
    
@admin.register(LogIntegration)
class LogIntegrationAdmin(admin.ModelAdmin):
    list_display = ('client', 'created_at')
    search_fields = ('client__name',)  # Ajuste conforme necessário para os campos do seu modelo Client
    list_filter = ('created_at',)
    readonly_fields = ('created_at',)  

@admin.register(Syncing)
class SyncingAdmin(admin.ModelAdmin):
    list_display = ('client', 'created_at', 'updated_at', 'status')
    search_fields = ('client__name',)        
