from django.conf import settings
from django.db import models


class DeviceToken(models.Model):
    """A Firebase Cloud Messaging token of one of the traveller's devices."""
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='devices')
    token = models.CharField(max_length=512, unique=True)
    platform = models.CharField(max_length=20, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    last_seen_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'{self.user} ({self.platform})'
