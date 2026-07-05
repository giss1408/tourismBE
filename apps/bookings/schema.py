import graphene
from graphene_django import DjangoObjectType
from django.db.models import Q
from .models import Booking


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

class UpsertBookings(graphene.Mutation):
    class Arguments:
        bookings = graphene.List(BookingInputType, required=True)

    ok = graphene.Boolean()

    def mutate(self, info, bookings):
        user = _require_auth(info)

        for item in bookings:
            defaults = dict(
                reference=item.reference,
                destination_id=item.destination_id,
                destination_name=item.destination_name,
                destination_image=getattr(item, 'destination_image', '') or '',
                location=getattr(item, 'location', '') or '',
                check_in_date=item.check_in_date[:10],
                check_out_date=item.check_out_date[:10],
                guests=getattr(item, 'guests', 1) or 1,
                nights=getattr(item, 'nights', 1) or 1,
                total_price=getattr(item, 'total_price', 0.0) or 0.0,
                status=getattr(item, 'status', 'Pending') or 'Pending',
                notes=getattr(item, 'notes', '') or '',
            )
            Booking.objects.update_or_create(
                user=user,
                reference=item.reference,
                defaults=defaults,
            )

        return UpsertBookings(ok=True)


class BookingMutation(graphene.ObjectType):
    upsert_bookings = UpsertBookings.Field()
