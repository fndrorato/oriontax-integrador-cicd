from django.contrib import admin
from .models import Task

@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = ('description', 'execution_time', 'last_execution', 'next_execution')
    search_fields = ('description',)
