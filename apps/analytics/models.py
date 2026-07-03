from django.conf import settings
from django.db import models


class AnalyticsEvent(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name='analytics_events',
    )
    name = models.CharField(max_length=200, db_index=True)
    properties = models.JSONField(default=dict)
    timestamp = models.DateTimeField(db_index=True)
    received_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-timestamp']

    def __str__(self):
        return f'{self.name} @ {self.timestamp}'


class UserProperties(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='analytics_properties',
    )
    properties = models.JSONField(default=dict)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'UserProperties({self.user})'
