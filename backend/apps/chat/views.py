from django.db.models import Count
from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from openai import OpenAI
from django.conf import settings

from .models import ChatSession, Message
from .serializers import ChatSessionSerializer, MessageSerializer


class ChatSessionListCreateView(generics.ListCreateAPIView):
    """
    GET  — List all chat sessions for the authenticated user.
    POST — Create a new chat session.
    """

    serializer_class = ChatSessionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return (
            ChatSession.objects
            .filter(user=self.request.user)
            .annotate(message_count=Count('messages'))
        )

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class ChatSessionDetailView(generics.RetrieveDestroyAPIView):
    """
    GET    — Retrieve a single chat session (scoped to user).
    DELETE — Destroy a session and its messages (cascade).
    """

    serializer_class = ChatSessionSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = 'id'

    def get_queryset(self):
        return (
            ChatSession.objects
            .filter(user=self.request.user)
            .annotate(message_count=Count('messages'))
        )


class MessageListCreateView(generics.ListCreateAPIView):
    """
    GET  — Return all messages for a session, ordered by created_at.
    POST — Accept { content }, call OpenAI, save both user & assistant messages.
    """

    serializer_class = MessageSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        session_id = self.kwargs['session_id']
        return Message.objects.filter(
            session_id=session_id,
            session__user=self.request.user,
        )

    def create(self, request, *args, **kwargs):
        session_id = self.kwargs['session_id']

        # Verify session belongs to user
        try:
            session = ChatSession.objects.get(
                id=session_id, user=request.user
            )
        except ChatSession.DoesNotExist:
            return Response(
                {'detail': 'Session not found.'},
                status=status.HTTP_404_NOT_FOUND,
            )

        user_content = request.data.get('content', '').strip()
        if not user_content:
            return Response(
                {'detail': 'Content is required.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Save the user message
        user_msg = Message.objects.create(
            session=session,
            role='user',
            content=user_content,
        )

        # Build conversation history for OpenAI
        history = list(
            session.messages.order_by('created_at').values_list('role', 'content')
        )
        openai_messages = [{'role': r, 'content': c} for r, c in history]

        # Call OpenAI
        try:
            client = OpenAI(api_key=settings.OPENAI_API_KEY)
            response = client.chat.completions.create(
                model=settings.OPENAI_MODEL,
                messages=openai_messages,
            )
            assistant_content = response.choices[0].message.content
            tokens = response.usage.total_tokens if response.usage else 0
        except Exception as e:
            assistant_content = f"Error communicating with AI: {str(e)}"
            tokens = 0

        # Save the assistant message
        assistant_msg = Message.objects.create(
            session=session,
            role='assistant',
            content=assistant_content,
            tokens_used=tokens,
        )

        serializer = MessageSerializer(assistant_msg)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
