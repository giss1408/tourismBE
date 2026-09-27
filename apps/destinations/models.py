from django.conf import settings
from django.db import models


def public_url(file_field):
    """Absolute URL of an uploaded file, for the apps."""
    return f'{settings.PUBLIC_BASE_URL.rstrip("/")}{file_field.url}'


class Destination(models.Model):
    name = models.CharField(max_length=200)
    description = models.TextField()
    location = models.CharField(max_length=200)
    # Average of the visible reviews, kept up to date by apps.reviews.
    rating = models.FloatField(default=0.0)
    review_count = models.PositiveIntegerField(default=0)
    price = models.FloatField(default=0.0)
    # Legacy image URLs, used until photos are uploaded (see Media).
    images = models.JSONField(default=list)
    activities = models.JSONField(default=list)
    is_featured = models.BooleanField(default=False)
    category = models.CharField(max_length=100)
    available_spots = models.IntegerField(default=50)
    discount = models.FloatField(default=0.0)
    # Drafts are only visible to managers.
    is_published = models.BooleanField(default=True)
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-is_featured', '-rating']

    def __str__(self):
        return self.name

    def image_urls(self):
        uploaded = [public_url(m.file) for m in self.media.all() if m.kind == Media.IMAGE]
        if uploaded:
            return uploaded
        return self.images if isinstance(self.images, list) else []

    def video_urls(self):
        return [public_url(m.file) for m in self.media.all() if m.kind == Media.VIDEO]


class Tour(models.Model):
    """A guided tour or excursion at a destination."""
    destination = models.ForeignKey(
        Destination, on_delete=models.CASCADE, related_name='tours')
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    duration_hours = models.FloatField(default=3)
    # Per person, in euros.
    price = models.FloatField(default=0)
    max_group_size = models.PositiveSmallIntegerField(default=12)
    # Language codes the tour is offered in, e.g. ["fr", "en", "de"].
    languages = models.JSONField(default=list)
    guide = models.ForeignKey(
        'guides.Guide', null=True, blank=True, on_delete=models.SET_NULL,
        related_name='tours')
    is_published = models.BooleanField(default=False)
    position = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['position', 'id']

    def __str__(self):
        return f'{self.destination} – {self.title}'

    def image_urls(self):
        return [public_url(m.file) for m in self.media.all() if m.kind == Media.IMAGE]

    def video_urls(self):
        return [public_url(m.file) for m in self.media.all() if m.kind == Media.VIDEO]


class Media(models.Model):
    """A photo or video of a destination or a tour; the first photo is the cover."""
    IMAGE = 'image'
    VIDEO = 'video'
    KIND_CHOICES = [(IMAGE, 'Photo'), (VIDEO, 'Video')]

    destination = models.ForeignKey(
        Destination, null=True, blank=True, on_delete=models.CASCADE, related_name='media')
    tour = models.ForeignKey(
        Tour, null=True, blank=True, on_delete=models.CASCADE, related_name='media')
    kind = models.CharField(max_length=10, choices=KIND_CHOICES)
    file = models.FileField(upload_to='media/%Y/%m/')
    position = models.PositiveIntegerField(default=0)
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['position', 'id']
        constraints = [
            models.CheckConstraint(
                condition=(models.Q(destination__isnull=False, tour__isnull=True)
                       | models.Q(destination__isnull=True, tour__isnull=False)),
                name='media_belongs_to_one_owner',
            ),
        ]

    def __str__(self):
        return f'{self.kind} {self.file.name}'
