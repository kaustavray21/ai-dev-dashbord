from rest_framework import serializers
from .models import ChatSession, Message


class MessageSerializer(serializers.ModelSerializer):
    """Serializer for individual chat messages."""

    class Meta:
        model = Message
        fields = [
            'id', 'session', 'role', 'content',
            'tool_calls', 'tokens_used', 'created_at',
        ]
        read_only_fields = ['id', 'session', 'role', 'tool_calls', 'tokens_used', 'created_at']


class ChatSessionSerializer(serializers.ModelSerializer):
    """Serializer for chat sessions with an annotated message count."""

    message_count = serializers.IntegerField(read_only=True, default=0)

    class Meta:
        model = ChatSession
        fields = [
            'id', 'user', 'title', 'context_type',
            'created_at', 'meta', 'message_count',
        ]
        read_only_fields = ['id', 'user', 'created_at', 'message_count']
