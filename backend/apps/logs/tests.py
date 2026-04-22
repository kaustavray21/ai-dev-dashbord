from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from apps.users.models import User
from .models import LogFile
from unittest.mock import patch
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone


class LogFileTests(APITestCase):

    def setUp(self):
        self.user1 = User.objects.create_user(username='user1', password='password')
        self.user2 = User.objects.create_user(username='user2', password='password')
        
        self.upload_url = reverse('log-upload')
        self.list_url = reverse('log-list')

    def test_upload_requires_auth(self):
        """Ensure unauthenticated users cannot upload logs."""
        response = self.client.post(self.upload_url, {})
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_upload_log_file_stores_content(self):
        """Ensure log files can be uploaded and text content is saved."""
        self.client.force_authenticate(user=self.user1)
        
        test_file = SimpleUploadedFile(
            name='test.log',
            content=b'INFO: application started\nERROR: null pointer exception',
            content_type='text/plain'
        )
        
        response = self.client.post(self.upload_url, {'file': test_file}, format='multipart')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(LogFile.objects.count(), 1)
        
        log_file = LogFile.objects.first()
        self.assertEqual(log_file.name, 'test.log')
        self.assertEqual(log_file.user, self.user1)
        self.assertIn('null pointer', log_file.content)
        self.assertEqual(log_file.file_size, len(b'INFO: application started\nERROR: null pointer exception'))

    def test_list_logs_returns_only_own_files(self):
        """Ensure users only see their own log files."""
        LogFile.objects.create(user=self.user1, name='user1.log', content='log1', file_size=4)
        LogFile.objects.create(user=self.user2, name='user2.log', content='log2', file_size=4)
        
        self.client.force_authenticate(user=self.user1)
        response = self.client.get(self.list_url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['name'], 'user1.log')


class LogAnalysisTests(APITestCase):

    def setUp(self):
        self.user = User.objects.create_user(username='user', password='password')
        self.log_file = LogFile.objects.create(
            user=self.user, 
            name='app.log', 
            content='ERROR: Connection timeout', 
            file_size=25
        )
        self.analysis_url = reverse('log-analysis', kwargs={'id': self.log_file.id})

    def test_analysis_endpoint_returns_cached_result_if_exists(self):
        """Ensure we don't call OpenAI if analysis is already done."""
        cached_analysis = {"summary": "Timeout error", "errors": ["Timeout"], "suggestions": ["Retry"]}
        self.log_file.analysis = cached_analysis
        self.log_file.analyzed_at = timezone.now()
        self.log_file.save()
        
        self.client.force_authenticate(user=self.user)
        response = self.client.get(self.analysis_url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, cached_analysis)

    @patch('apps.logs.views.OpenAI')
    def test_analysis_calls_openai_on_first_request(self, MockOpenAI):
        """Ensure first request calls OpenAI, parses JSON, and saves it."""
        # Setup mock OpenAI JSON response
        mock_client = MockOpenAI.return_value
        mock_response = mock_client.chat.completions.create.return_value
        mock_json_string = '{"summary": "A mock summary", "errors": ["Mock error"], "suggestions": ["Mock fix"]}'
        mock_response.choices = [type('obj', (object,), {'message': type('obj', (object,), {'content': mock_json_string})})]

        self.client.force_authenticate(user=self.user)
        response = self.client.get(self.analysis_url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['summary'], "A mock summary")
        
        # Verify it was saved to DB
        self.log_file.refresh_from_db()
        self.assertIsNotNone(self.log_file.analysis)
        self.assertIsNotNone(self.log_file.analyzed_at)
        self.assertEqual(self.log_file.analysis['summary'], "A mock summary")
