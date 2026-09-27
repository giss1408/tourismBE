from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models import Avg, Count


class Review(models.Model):
    destination = models.ForeignKey(
        'destinations.Destination', on_delete=models.CASCADE, related_name='reviews')
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='reviews')
    rating = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)])
    comment = models.TextField(max_length=2000, blank=True)
    # Moderators can hide a review without deleting it.
    is_visible = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        constraints = [
            models.UniqueConstraint(fields=['destination', 'user'],
                                    name='one_review_per_traveller'),
        ]

    def __str__(self):
        return f'{self.destination} – {self.rating}/5'


def refresh_destination_rating(destination):
    """Recomputes the destination's average rating from visible reviews."""
    stats = destination.reviews.filter(is_visible=True).aggregate(
        average=Avg('rating'), count=Count('id'))
    destination.rating = round(stats['average'] or 0.0, 1)
    destination.review_count = stats['count']
    destination.save(update_fields=['rating', 'review_count'])
