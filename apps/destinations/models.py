from django.contrib.postgres.fields import ArrayField
from django.db import models


class Destination(models.Model):
    name = models.CharField(max_length=200)
    description = models.TextField()
    location = models.CharField(max_length=200)
    rating = models.FloatField(default=0.0)
    price = models.FloatField(default=0.0)
    images = models.JSONField(default=list)
    activities = models.JSONField(default=list)
    is_featured = models.BooleanField(default=False)
    category = models.CharField(max_length=100)
    available_spots = models.IntegerField(default=50)
    discount = models.FloatField(default=0.0)
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-is_featured', '-rating']

    def __str__(self):
        return self.name
