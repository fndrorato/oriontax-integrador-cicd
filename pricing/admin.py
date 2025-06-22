from django.contrib import admin
from pricing.models import (
    UsersCosts, 
    CostsMaster, 
    CostsDetail, 
    ItemClass, 
    Pricing
)

@admin.register(UsersCosts)
class UsersCostsAdmin(admin.ModelAdmin):
    list_display = ('user', 'description', 'created_at', 'updated_at')
    search_fields = ('user__username', 'description')
    list_filter = ('created_at', 'updated_at')

@admin.register(CostsMaster)
class CostsMasterAdmin(admin.ModelAdmin):
    list_display = ('user', 'sales_per_month', 'created_at', 'updated_at')
    search_fields = ('user__username',)
    list_filter = ('created_at', 'updated_at')

@admin.register(CostsDetail)
class CostsDetailAdmin(admin.ModelAdmin):
    list_display = ('costs_master', 'user_costs', 'value', 'created_at', 'updated_at')
    search_fields = ('costs_master__user__username', 'user_costs__description')
    list_filter = ('created_at', 'updated_at')  

@admin.register(ItemClass)
class ItemClassAdmin(admin.ModelAdmin):
    list_display = ('name', 'icms_value', 'pis_value', 'cofins_value', 'active', 'created_at', 'updated_at')
    search_fields = ('name',)
    list_filter = ('active', 'created_at', 'updated_at')    

@admin.register(Pricing)
class PricingAdmin(admin.ModelAdmin):
    list_display = (
        'user', 'description', 'item_class', 'item_icms_excluded', 
        'items_pis_cofins_excluded', 'supplier', 'total_cost_at_moment', 
        'markup', 'card_tax', 'cost_price', 'sale_price', 'created_at', 'updated_at'
    )
    search_fields = ('user__username', 'description', 'item_class__name')
    list_filter = ('created_at', 'updated_at')
