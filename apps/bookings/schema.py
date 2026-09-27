import graphene
from django.conf import settings
from django.utils.dateparse import parse_date
from graphene_django import DjangoObjectType

from apps.core.emails import send_booking_email
from apps.destinations.models import Destination

from .models import Booking
from .services import cancel_booking, free_cancellation_deadline

MAX_GUESTS = 20
MAX_NIGHTS = 90


class BookingType(DjangoObjectType):
    class Meta:
        model = Booking
        fields = (
            'id', 'reference', 'destination_id', 'destination_name',
            'destination_image', 'location', 'booking_date',
            'check_in_date', 'check_out_date', 'guests', 'nights',
            'total_price', 'status', 'notes',
        )

    # Expose camelCase aliases matching the Flutter DTO
    destination_id = graphene.String()
    destination_name = graphene.String()
    destination_image = graphene.String()
    booking_date = graphene.String()
    check_in_date = graphene.String()
    check_out_date = graphene.String()
    total_price = graphene.Float()
    is_paid = graphene.Boolean()
    free_cancellation_until = graphene.String()

    def resolve_is_paid(self, info):
        return self.payments.filter(status='succeeded').exists()

    def resolve_free_cancellation_until(self, info):
        return free_cancellation_deadline(self).isoformat()

    def resolve_booking_date(self, info):
        return self.booking_date.isoformat()

    def resolve_check_in_date(self, info):
        return self.check_in_date.isoformat()

    def resolve_check_out_date(self, info):
        return self.check_out_date.isoformat()


class BookingInputType(graphene.InputObjectType):
    id = graphene.String(required=True)
    reference = graphene.String(required=True)
    destination_id = graphene.String(required=True)
    destination_name = graphene.String(required=True)
    destination_image = graphene.String()
    location = graphene.String()
    booking_date = graphene.String()
    check_in_date = graphene.String(required=True)
    check_out_date = graphene.String(required=True)
    guests = graphene.Int()
    nights = graphene.Int()
    total_price = graphene.Float()
    status = graphene.String()
    notes = graphene.String()


def _require_auth(info):
    user = info.context.user
    if not user or not user.is_authenticated:
        raise Exception('UNAUTHENTICATED')
    return user


# ─────────── Queries ───────────

class BookingQuery(graphene.ObjectType):
    bookings = graphene.List(
        BookingType,
        user_id=graphene.String(),
        status=graphene.String(),
        sort_by=graphene.String(),
        sort_direction=graphene.String(),
        page=graphene.Int(),
        page_size=graphene.Int(),
    )

    def resolve_bookings(
        self, info,
        user_id=None, status=None,
        sort_by=None, sort_direction=None,
        page=None, page_size=None,
    ):
        user = _require_auth(info)
        qs = Booking.objects.filter(user=user)

        if status and status.strip():
            qs = qs.filter(status__iexact=status.strip())

        sort_field = sort_by or 'booking_date'
        allowed_sort = {'booking_date', 'check_in_date', 'total_price', 'status'}
        if sort_field not in allowed_sort:
            sort_field = 'booking_date'
        prefix = '-' if (sort_direction or 'desc').lower() == 'desc' else ''
        qs = qs.order_by(f'{prefix}{sort_field}')

        page = max(1, page or 1)
        page_size = min(100, max(1, page_size or 20))
        offset = (page - 1) * page_size
        return qs[offset: offset + page_size]


# ─────────── Mutations ───────────

def _booking_values(item, existing):
    """Validated fields for a booking; the server decides price and status.

    The app only chooses the destination, dates and guests. The price comes
    from the destination, and the app can at most cancel: confirming a
    booking is up to the operator (or a verified payment).
    """
    check_in = parse_date((item.check_in_date or '')[:10])
    check_out = parse_date((item.check_out_date or '')[:10])
    if check_in is None or check_out is None:
        raise Exception('Invalid booking dates.')
    nights = (check_out - check_in).days
    if not 1 <= nights <= MAX_NIGHTS:
        raise Exception('Invalid booking dates.')
    guests = getattr(item, 'guests', None) or 1
    if not 1 <= guests <= MAX_GUESTS:
        raise Exception('Invalid number of guests.')

    destination = None
    if str(item.destination_id).isdigit():
        destination = Destination.objects.filter(
            pk=int(item.destination_id), is_published=True).first()
    if destination is None and existing is None:
        raise Exception('Unknown destination.')

    # Cancelling goes through cancel_booking() (refund rules); the app can
    # never confirm a booking itself.
    status = existing.status if existing is not None else Booking.STATUS_PENDING

    values = dict(
        check_in_date=check_in,
        check_out_date=check_out,
        guests=guests,
        nights=nights,
        status=status,
        notes=(getattr(item, 'notes', '') or '')[:2000],
    )
    if destination is not None:
        unit_price = destination.price * (1 - destination.discount) \
            if destination.discount > 0 else destination.price
        images = destination.image_urls()
        values.update(
            destination_id=str(destination.pk),
            destination_name=destination.name,
            destination_image=images[0] if images else '',
            location=destination.location,
            total_price=round(
                unit_price * nights * guests + settings.BOOKING_SERVICE_FEE_EUR, 2),
        )
    return values


class UpsertBookings(graphene.Mutation):
    class Arguments:
        bookings = graphene.List(BookingInputType, required=True)

    ok = graphene.Boolean()

    def mutate(self, info, bookings):
        user = _require_auth(info)
        if len(bookings) > 100:
            raise Exception('Too many bookings in one request.')

        for item in bookings:
            existing = Booking.objects.filter(
                user=user, reference=item.reference).first()
            if existing is not None and existing.status == Booking.STATUS_CANCELLED:
                continue  # A cancellation is final.
            values = _booking_values(item, existing)
            if existing is None:
                booking = Booking.objects.create(
                    user=user, reference=item.reference, **values)
                send_booking_email(booking, 'booking_received')
            else:
                for field, value in values.items():
                    setattr(existing, field, value)
                existing.save()
                booking = existing
            if getattr(item, 'status', None) == Booking.STATUS_CANCELLED:
                cancel_booking(booking)

        return UpsertBookings(ok=True)


class CancelBooking(graphene.Mutation):
    """Cancels a booking; refunded in full when inside the free window."""

    class Arguments:
        reference = graphene.String(required=True)

    ok = graphene.Boolean()
    refunded = graphene.Boolean()

    def mutate(self, info, reference):
        user = _require_auth(info)
        booking = Booking.objects.filter(user=user, reference=reference).first()
        if booking is None:
            raise Exception('Booking not found.')
        refunded = cancel_booking(booking)
        return CancelBooking(ok=True, refunded=refunded)


class BookingMutation(graphene.ObjectType):
    upsert_bookings = UpsertBookings.Field()
    cancel_booking = CancelBooking.Field()
