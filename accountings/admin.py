from django.contrib import admin
from .models import Accounting

@admin.register(Accounting)
class AccountingAdmin(admin.ModelAdmin):
    list_display = ('name', 'city', 'email', 'phone', 'contact')
    search_fields = ('name', 'email', 'phone', 'contact')
    list_filter = ('city',)
