from django.db import models
from django.conf import settings

class LogFile(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    name = models.CharField(max_length=255)
    content = models.TextField()
    file_size = models.IntegerField()
    analysis = models.JSONField(null=True, blank=True)
    analyzed_at = models.DateTimeField(null=True, blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} uploaded by {self.user.username}"
