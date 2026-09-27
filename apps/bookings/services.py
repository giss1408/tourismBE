"""Booking state changes, with their emails, pushes and refunds."""
import logging

from django.conf import settings
from django.utils import timezone

from apps.core.emails import send_booking_email

from .models import Booking

log = logging.getLogger(__name__)


def free_cancellation_deadline(booking):
    """Last day on which the booking can be cancelled with a full refund."""
    return booking.check_in_date - timezone.timedelta(days=settings.FREE_CANCELLATION_DAYS)


def can_cancel_for_free(booking, today=None):
    return (today or timezone.localdate()) <= free_cancellation_deadline(booking)


def confirm_booking(booking):
    """Confirms a pending booking and tells the traveller."""
    if booking.status != Booking.STATUS_PENDING:
        return False
    booking.status = Booking.STATUS_CONFIRMED
    booking.confirmed_at = timezone.now()
    booking.save(update_fields=['status', 'confirmed_at'])
    send_booking_email(booking, 'booking_confirmed')
    from apps.notifications.push import notify_booking
    notify_booking(booking, 'booking_confirmed')
    return True


def cancel_booking(booking):
    """Cancels the booking; refunds it when cancelled in time.

    Returns True when a refund was issued.
    """
    if booking.status == Booking.STATUS_CANCELLED:
        return False
    refunded = False
    if can_cancel_for_free(booking):
        from apps.payments.services import refund_booking
        refunded = refund_booking(booking)
    booking.status = Booking.STATUS_CANCELLED
    booking.cancelled_at = timezone.now()
    booking.save(update_fields=['status', 'cancelled_at'])
    send_booking_email(booking, 'booking_cancelled')
    return refunded
