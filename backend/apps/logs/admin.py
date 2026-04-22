from django.contrib import admin
from .models import LogFile

@admin.register(LogFile)
class LogFileAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'user', 'file_size', 'analyzed_at', 'uploaded_at')
    list_filter = ('uploaded_at', 'analyzed_at')
    search_fields = ('name', 'user__username')
    readonly_fields = ('uploaded_at', 'analyzed_at')
