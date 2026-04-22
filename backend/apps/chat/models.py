import uuid
from django.db import models
from django.conf import settings


class ChatSession(models.Model):
    """A chat session/conversation belonging to a user."""

    CONTEXT_CHOICES = [
        ('general', 'General'),
        ('code', 'Code'),
        ('logs', 'Logs'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='chat_sessions',
    )
    title = models.CharField(max_length=255, blank=True)
    context_type = models.CharField(
        max_length=20, choices=CONTEXT_CHOICES, default='general'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    meta = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.title or 'Untitled'} ({self.user.username})"


class Message(models.Model):
    """A single message inside a ChatSession."""

    ROLE_CHOICES = [
        ('user', 'User'),
        ('assistant', 'Assistant'),
        ('system', 'System'),
    ]

    session = models.ForeignKey(
        ChatSession,
        on_delete=models.CASCADE,
        related_name='messages',
    )
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)
    content = models.TextField()
    tool_calls = models.JSONField(null=True, blank=True)
    tokens_used = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"[{self.role}] {self.content[:50]}"
