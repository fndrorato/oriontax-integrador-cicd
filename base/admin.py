from django.contrib import admin
from base.models import States, Costs


@admin.register(States)
class StatesAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'aliquota_inter')
    list_filter = ('aliquota_inter',)
    search_fields = ('name', 'code')
    ordering = ('name',)

@admin.register(Costs)
class CostsAdmin(admin.ModelAdmin):
    list_display = ('name', 'active')
    list_filter = ('active',)
    search_fields = ('name',)
    ordering = ('name',)
