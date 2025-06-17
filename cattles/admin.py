from cattles.models import (
    FieldConfiguration, 
    FieldOption, 
    MatrixSimulation,
    MeatCut,
    UserMeatCut,
    ButcheryMaster,
    ButcheryDetail
)
from django.contrib import admin


class FieldOptionInline(admin.TabularInline):
    model = FieldOption
    extra = 1


@admin.register(FieldConfiguration)
class FieldConfigurationAdmin(admin.ModelAdmin):
    list_display = ('field_name', 'field_label', 'description')
    search_fields = ('field_name', 'field_label')
    inlines = [FieldOptionInline]


@admin.register(FieldOption)
class FieldOptionAdmin(admin.ModelAdmin):
    list_display = ('field', 'label', 'value')
    list_filter = ('field',)
    search_fields = ('label', 'value')


@admin.register(MatrixSimulation)
class MatrixSimulationAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'description', 'cow_weighing_location', 'created_at')
    list_filter = ('user', 'cow_weighing_location', 'created_at')
    search_fields = ('description', 'user__username')
    readonly_fields = ('created_at', 'updated_at')

    fieldsets = (
        (None, {
            'fields': ('user', 'description', 'cow_weighing_location')
        }),
        ('Volume e Preço de Venda', {
            'fields': ('monthly_sales_volume_kg', 'average_price_per_kg', 'total_sales_per_month')
        }),
        ('Peso Médio por Vaca', {
            'fields': (
                'mean_weight_per_cow_producer_kg',
                'mean_weight_per_cow_slaughterhouse_kg',
                'mean_weight_per_cow_producer_arroba',
                'mean_weight_per_cow_slaughterhouse_arroba'
            )
        }),
        ('Rendimentos (%)', {
            'fields': ('yield_live_cow_pasture_percent', 'yield_butchered_cow_percent')
        }),
        ('Preços', {
            'fields': (
                'price_per_arroba_producer',
                'price_per_arroba_slaughterhouse',
                'price_per_kg_butchered_cow'
            )
        }),
        ('Serviços e ICMS', {
            'fields': (
                'slaughter_service_per_cow_producer',
                'slaughter_service_per_cow_slaughterhouse',
                'icms_debit_percent',
                'icms_credit_percent',
                'granted_credit_percent',
                'icms_loss_reversal_percent',
                'protege_percent',
                'fundeinfra_percent'
            )
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at')
        }),
    )

@admin.register(MeatCut)
class MeatCutAdmin(admin.ModelAdmin):
    list_display = ('name', 'active', 'created_by', 'created_at', 'updated_at')
    list_filter = ('active',)
    search_fields = ('name',)
    readonly_fields = ('created_at', 'updated_at')


@admin.register(UserMeatCut)
class UserMeatCutAdmin(admin.ModelAdmin):
    list_display = ('user', 'meat_cut', 'created_at', 'updated_at')
    search_fields = ('user__username', 'meat_cut')
    readonly_fields = ('created_at', 'updated_at')


@admin.register(ButcheryMaster)
class ButcheryMasterAdmin(admin.ModelAdmin):
    list_display = ('user', 'arroba_price_nf', 'invoice_weight', 'cost_per_kg', 'created_at', 'updated_at')
    search_fields = ('user__username',)
    readonly_fields = ('created_at', 'updated_at')


@admin.register(ButcheryDetail)
class ButcheryDetailAdmin(admin.ModelAdmin):
    list_display = ('user_meat_cut', 'selling_price', 'created_at', 'updated_at')
    search_fields = ('user_meat_cut__meat_cut', 'user_meat_cut__user__username')
    readonly_fields = ('created_at', 'updated_at')
