from django.utils import timezone
from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser
from openai import OpenAI
from django.conf import settings
import json

from .models import LogFile
from .serializers import LogFileSerializer


class LogListView(generics.ListAPIView):
    """
    GET /api/logs/
    List user's log files.
    """
    serializer_class = LogFileSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return LogFile.objects.filter(user=self.request.user).order_by('-uploaded_at')


class LogUploadView(generics.CreateAPIView):
    """
    POST /api/logs/upload/
    Upload a log file. Reads content, saves to DB, returns standard response.
    """
    serializer_class = LogFileSerializer
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def create(self, request, *args, **kwargs):
        file_obj = request.FILES.get('file')
        if not file_obj:
            return Response({'detail': 'No file uploaded.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            content = file_obj.read().decode('utf-8')
        except UnicodeDecodeError:
            return Response({'detail': 'File must be text-based (utf-8).'}, status=status.HTTP_400_BAD_REQUEST)

        log_file = LogFile.objects.create(
            user=request.user,
            name=file_obj.name,
            content=content,
            file_size=file_obj.size
        )

        serializer = self.get_serializer(log_file)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class LogAnalysisView(generics.RetrieveAPIView):
    """
    GET /api/logs/<id>/analysis/
    If analysis is cached, return it.
    Else call OpenAI to analyze the log file content, save, and return.
    """
    permission_classes = [IsAuthenticated]
    lookup_field = 'id'

    def get_queryset(self):
        return LogFile.objects.filter(user=self.request.user)

    def retrieve(self, request, *args, **kwargs):
        log_file = self.get_object()

        if log_file.analysis:
            return Response(log_file.analysis, status=status.HTTP_200_OK)

        # Build prompt for OpenAI
        # Truncate content to avoid exceeding token limits for a typical prompt
        content_preview = log_file.content[:15000] 
        prompt = f"""
You are an expert software engineer analyzing a server or application log file.
Please analyze the following log snippet and provide your findings in valid JSON format.
Make sure the JSON contains exactly these keys:
- "summary": A brief summary of what the logs represent.
- "errors": An array of strings describing any errors or warnings found.
- "suggestions": An array of strings suggesting possible fixes or next steps.

Log Content:
{content_preview}
"""

        try:
            client = OpenAI(api_key=settings.OPENAI_API_KEY)
            response = client.chat.completions.create(
                model=settings.OPENAI_MODEL,
                response_format={ "type": "json_object" },
                messages=[
                    {"role": "system", "content": "You output JSON matching the exact schema requested."},
                    {"role": "user", "content": prompt}
                ]
            )
            analysis_text = response.choices[0].message.content
            analysis_json = json.loads(analysis_text)
        except Exception as e:
            return Response({'detail': f'Analysis failed: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        # Cache analysis in DB
        log_file.analysis = analysis_json
        log_file.analyzed_at = timezone.now()
        log_file.save()

        return Response(analysis_json, status=status.HTTP_200_OK)
