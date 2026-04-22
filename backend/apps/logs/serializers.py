from rest_framework import serializers
from .models import LogFile

class LogFileSerializer(serializers.ModelSerializer):
    class Meta:
        model = LogFile
        fields = ['id', 'user', 'name', 'content', 'file_size', 'analysis', 'analyzed_at', 'uploaded_at']
        read_only_fields = ['id', 'user', 'file_size', 'analysis', 'analyzed_at', 'uploaded_at']
        extra_kwargs = {
            'content': {'write_only': True}
        }
