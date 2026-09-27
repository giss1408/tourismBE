from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.bookings.models import Booking
from apps.notifications.push import notify_booking


class Command(BaseCommand):
    help = 'Reminds travellers the day before a confirmed stay. Run daily (cron).'

    def handle(self, *args, **options):
        tomorrow = timezone.localdate() + timezone.timedelta(days=1)
        bookings = Booking.objects.filter(
            status=Booking.STATUS_CONFIRMED,
            check_in_date=tomorrow,
            reminder_sent_at__isnull=True,
        ).select_related('user')
        count = 0
        for booking in bookings:
            notify_booking(booking, 'trip_reminder')
            booking.reminder_sent_at = timezone.now()
            booking.save(update_fields=['reminder_sent_at'])
            count += 1
        self.stdout.write(f'Sent {count} trip reminder(s).')
