from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from .models import Review, refresh_destination_rating


@receiver(post_save, sender=Review)
@receiver(post_delete, sender=Review)
def _update_rating(sender, instance, **kwargs):
    refresh_destination_rating(instance.destination)
