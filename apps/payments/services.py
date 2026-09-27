"""Stripe integration. Every call is a no-op when Stripe is not configured."""
import logging

import stripe
from django.conf import settings

from .models import Payment

log = logging.getLogger(__name__)


class PaymentsUnavailable(Exception):
    pass


def payments_enabled():
    return bool(settings.STRIPE_SECRET_KEY and settings.STRIPE_PUBLISHABLE_KEY)


def _client():
    if not payments_enabled():
        raise PaymentsUnavailable('Online payment is not available yet.')
    return stripe.StripeClient(settings.STRIPE_SECRET_KEY)


def amount_in_cents(booking):
    return int(round(booking.total_price * 100))


def create_or_reuse_payment_intent(booking):
    """The PaymentIntent to pay [booking], reusing an unpaid one if any.

    Payment methods (card, PayPal, Apple Pay, Google Pay…) are chosen in the
    Stripe dashboard: automatic_payment_methods lets Stripe offer them all.
    """
    client = _client()
    amount = amount_in_cents(booking)
    pending = booking.payments.filter(status=Payment.STATUS_PENDING).first()
    if pending is not None:
        intent = client.v1.payment_intents.retrieve(pending.stripe_payment_intent_id)
        if intent.status not in ('succeeded', 'canceled') and intent.amount == amount:
            return intent
    params = {
        'amount': amount,
        'currency': settings.PAYMENT_CURRENCY,
        'automatic_payment_methods': {'enabled': True},
        'description': f'{settings.COMPANY_NAME} – {booking.destination_name}',
        'metadata': {'booking_reference': booking.reference},
    }
    if booking.user and booking.user.email:
        params['receipt_email'] = booking.user.email
    intent = client.v1.payment_intents.create(params=params)
    Payment.objects.create(
        booking=booking,
        stripe_payment_intent_id=intent.id,
        amount=amount,
        currency=settings.PAYMENT_CURRENCY,
    )
    return intent


def mark_succeeded(payment_intent_id):
    """Webhook: payment received, so the booking is confirmed."""
    from apps.bookings.services import confirm_booking

    payment = Payment.objects.select_related('booking').filter(
        stripe_payment_intent_id=payment_intent_id).first()
    if payment is None or payment.status == Payment.STATUS_SUCCEEDED:
        return
    payment.status = Payment.STATUS_SUCCEEDED
    payment.save(update_fields=['status', 'updated_at'])
    confirm_booking(payment.booking)


def mark_failed(payment_intent_id):
    Payment.objects.filter(
        stripe_payment_intent_id=payment_intent_id,
        status=Payment.STATUS_PENDING,
    ).update(status=Payment.STATUS_FAILED)


def refund_booking(booking):
    """Refunds every successful payment of [booking]. True if any was."""
    paid = list(booking.payments.filter(status=Payment.STATUS_SUCCEEDED))
    if not paid:
        return False
    client = _client()
    for payment in paid:
        client.v1.refunds.create(params={'payment_intent': payment.stripe_payment_intent_id})
        payment.status = Payment.STATUS_REFUNDED
        payment.save(update_fields=['status', 'updated_at'])
    return True
