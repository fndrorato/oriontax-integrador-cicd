from django.contrib import admin
from .models import States


@admin.register(States)
class StatesAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'aliquota_inter')
    list_filter = ('aliquota_inter',)
    search_fields = ('name', 'code')
    ordering = ('name',)
