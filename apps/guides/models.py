from django.db import models


class Guide(models.Model):
    """A local guide travellers can contact for a guided tour."""
    name = models.CharField(max_length=150)
    bio = models.TextField(blank=True)
    # Language codes the guide speaks, e.g. ["fr", "en", "de"].
    languages = models.JSONField(default=list)
    photo_url = models.URLField(blank=True)
    # International format without '+' or spaces, for wa.me links.
    whatsapp = models.CharField(max_length=20, blank=True)
    email = models.EmailField(blank=True)
    destinations = models.ManyToManyField(
        'destinations.Destination', related_name='guides', blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name
