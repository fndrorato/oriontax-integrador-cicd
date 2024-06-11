from django.contrib import admin
from .models import ERP

@admin.register(ERP)
class ERPModelAdmin(admin.ModelAdmin):
    list_display = ('name', 'description')   
