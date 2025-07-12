from django.contrib import admin
from .models import SupplierProfile, PriceQuote


@admin.register(SupplierProfile)
class SupplierProfileAdmin(admin.ModelAdmin):
    list_display = ('name', 'tax_value', 'description', 'only_shop_simulation')
    search_fields = ('name',)
    ordering = ('name',)


@admin.register(PriceQuote)
class PriceQuoteAdmin(admin.ModelAdmin):
    list_display = (
        'simulation_description', 'user', 'state_option_01', 'state_option_02',
        'product_icms_7', 'product_pis_cofins',
        'total_cost', 'best_option', 'created_at'
    )
    list_filter = ('product_icms_7', 'product_pis_cofins', 'best_option')
    search_fields = ('simulation_description', 'product_description', 'user__username')
    autocomplete_fields = ('user', 'state_option_01', 'state_option_02', 'best_option', 'supplier_profile_01', 'supplier_profile_02')
    readonly_fields = ('created_at', 'updated_at', 'total_cost', 'best_option', 'icms_credit', 'pis_cofins_credit')
    date_hierarchy = 'created_at'
