from django.db import models


class Payment(models.Model):
    """A Stripe PaymentIntent for a booking. Card details stay at Stripe."""

    STATUS_PENDING = 'pending'
    STATUS_SUCCEEDED = 'succeeded'
    STATUS_FAILED = 'failed'
    STATUS_REFUNDED = 'refunded'
    STATUS_CHOICES = [
        (STATUS_PENDING, 'Pending'),
        (STATUS_SUCCEEDED, 'Succeeded'),
        (STATUS_FAILED, 'Failed'),
        (STATUS_REFUNDED, 'Refunded'),
    ]

    booking = models.ForeignKey(
        'bookings.Booking', on_delete=models.PROTECT, related_name='payments')
    stripe_payment_intent_id = models.CharField(max_length=100, unique=True)
    # Smallest currency unit (cents).
    amount = models.PositiveIntegerField()
    currency = models.CharField(max_length=3, default='eur')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.booking.reference} – {self.amount / 100:.2f} {self.currency} ({self.status})'
