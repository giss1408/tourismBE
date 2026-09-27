import graphene
from django.conf import settings

from apps.bookings.models import Booking

from .services import PaymentsUnavailable, create_or_reuse_payment_intent


class PaymentSheetType(graphene.ObjectType):
    """What the app's Stripe PaymentSheet needs to take the payment."""
    client_secret = graphene.String()
    publishable_key = graphene.String()
    amount = graphene.Int()
    currency = graphene.String()
    merchant_display_name = graphene.String()


class CreateBookingPayment(graphene.Mutation):
    class Arguments:
        reference = graphene.String(required=True)

    Output = PaymentSheetType

    def mutate(self, info, reference):
        user = info.context.user
        if not user or not user.is_authenticated:
            raise Exception('UNAUTHENTICATED')
        booking = Booking.objects.filter(user=user, reference=reference).first()
        if booking is None:
            raise Exception('Booking not found.')
        if booking.status != Booking.STATUS_PENDING:
            raise Exception('This booking cannot be paid.')
        try:
            intent = create_or_reuse_payment_intent(booking)
        except PaymentsUnavailable as error:
            raise Exception(str(error))
        return PaymentSheetType(
            client_secret=intent.client_secret,
            publishable_key=settings.STRIPE_PUBLISHABLE_KEY,
            amount=intent.amount,
            currency=intent.currency,
            merchant_display_name=settings.COMPANY_NAME,
        )


class PaymentMutation(graphene.ObjectType):
    create_booking_payment = CreateBookingPayment.Field()
