from django.contrib import admin
from .models import ChatSession, Message


@admin.register(ChatSession)
class ChatSessionAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'title', 'context_type', 'created_at')
    list_filter = ('context_type', 'created_at')
    search_fields = ('title', 'user__username')
    readonly_fields = ('id', 'created_at')


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ('id', 'session', 'role', 'short_content', 'tokens_used', 'created_at')
    list_filter = ('role', 'created_at')
    search_fields = ('content',)
    readonly_fields = ('created_at',)

    @admin.display(description='Content')
    def short_content(self, obj):
        return obj.content[:80] + '...' if len(obj.content) > 80 else obj.content
