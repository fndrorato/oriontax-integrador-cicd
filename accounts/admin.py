from django.contrib import admin
from .models import Profile

@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'birth_date', 'phone', 'supervisor', 'manager')
    search_fields = ('user__username', 'user__email', 'phone')
    list_filter = ('supervisor', 'manager')
    fieldsets = (
        (None, {
            'fields': ('user', 'birth_date', 'phone')
        }),
        ('Permissions', {
            'fields': ('supervisor', 'manager'),
        }),
    )
