from django.contrib import admin
from api.models import FileMonitorStatus

@admin.register(FileMonitorStatus)
class FileMonitorStatusAdmin(admin.ModelAdmin):
    list_display = ('is_running', 'last_checked')
