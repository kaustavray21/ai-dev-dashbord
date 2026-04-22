from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from apps.users.models import User
from .models import ChatSession, Message
from unittest.mock import patch


class ChatSessionTests(APITestCase):

    def setUp(self):
        self.user1 = User.objects.create_user(username='user1', password='password')
        self.user2 = User.objects.create_user(username='user2', password='password')
        
        self.session_list_url = reverse('chat-session-list')

    def test_create_session_requires_auth(self):
        """Ensure unauthenticated users cannot create a session."""
        response = self.client.post(self.session_list_url, {'title': 'New Chat'})
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_create_session_returns_uuid(self):
        """Ensure an authenticated user can create a session and gets a UUID back."""
        self.client.force_authenticate(user=self.user1)
        response = self.client.post(self.session_list_url, {'title': 'My Chat'})
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('id', response.data)
        self.assertEqual(response.data['title'], 'My Chat')

    def test_list_sessions_only_returns_own_sessions(self):
        """Ensure users only see their own sessions."""
        ChatSession.objects.create(user=self.user1, title='User 1 Session')
        ChatSession.objects.create(user=self.user2, title='User 2 Session')

        self.client.force_authenticate(user=self.user1)
        response = self.client.get(self.session_list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['title'], 'User 1 Session')

    def test_delete_session_removes_messages(self):
        """Ensure deleting a session cascades and deletes its messages."""
        session = ChatSession.objects.create(user=self.user1, title='Delete Me')
        Message.objects.create(session=session, role='user', content='Hello')
        
        self.assertEqual(Message.objects.count(), 1)
        
        self.client.force_authenticate(user=self.user1)
        detail_url = reverse('chat-session-detail', kwargs={'id': session.id})
        response = self.client.delete(detail_url)
        
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(ChatSession.objects.count(), 0)
        self.assertEqual(Message.objects.count(), 0)


class ChatMessageTests(APITestCase):

    def setUp(self):
        self.user = User.objects.create_user(username='user', password='password')
        self.session = ChatSession.objects.create(user=self.user, title='Test Session')
        self.message_list_url = reverse('chat-message-list', kwargs={'session_id': self.session.id})

    @patch('apps.chat.views.OpenAI')
    def test_send_message_saves_user_and_assistant_turns(self, MockOpenAI):
        """Ensure posting a message saves the user message and mocked assistant response."""
        # Setup mock OpenAI response
        mock_client = MockOpenAI.return_value
        mock_response = mock_client.chat.completions.create.return_value
        mock_response.choices = [type('obj', (object,), {'message': type('obj', (object,), {'content': 'Mocked reply'})})]
        mock_response.usage = type('obj', (object,), {'total_tokens': 42})

        self.client.force_authenticate(user=self.user)
        response = self.client.post(self.message_list_url, {'content': 'Hello AI'})
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['content'], 'Mocked reply')
        self.assertEqual(response.data['tokens_used'], 42)

        # Check DB
        self.assertEqual(Message.objects.count(), 2)
        user_msg = Message.objects.get(role='user')
        assistant_msg = Message.objects.get(role='assistant')
        
        self.assertEqual(user_msg.content, 'Hello AI')
        self.assertEqual(assistant_msg.content, 'Mocked reply')

    def test_message_history_returned_in_order(self):
        """Ensure GET /messages returns messages ordered by created_at."""
        Message.objects.create(session=self.session, role='user', content='First')
        Message.objects.create(session=self.session, role='assistant', content='Second')
        
        self.client.force_authenticate(user=self.user)
        response = self.client.get(self.message_list_url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)
        self.assertEqual(response.data[0]['content'], 'First')
        self.assertEqual(response.data[1]['content'], 'Second')
