from django.conf import settings
from django.db import models


class Booking(models.Model):
    STATUS_CONFIRMED = 'Confirmed'
    STATUS_PENDING = 'Pending'
    STATUS_CANCELLED = 'Cancelled'
    STATUS_CHOICES = [
        (STATUS_CONFIRMED, 'Confirmed'),
        (STATUS_PENDING, 'Pending'),
        (STATUS_CANCELLED, 'Cancelled'),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='bookings',
    )
    reference = models.CharField(max_length=50, unique=True)
    destination_id = models.CharField(max_length=100)
    destination_name = models.CharField(max_length=200)
    destination_image = models.URLField(blank=True)
    location = models.CharField(max_length=200, blank=True)
    booking_date = models.DateTimeField(auto_now_add=True)
    check_in_date = models.DateField()
    check_out_date = models.DateField()
    guests = models.PositiveSmallIntegerField(default=1)
    nights = models.PositiveSmallIntegerField(default=1)
    total_price = models.FloatField(default=0.0)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ['-booking_date']

    def __str__(self):
        return f'{self.reference} – {self.destination_name}'
