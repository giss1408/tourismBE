import logging

import stripe
from django.conf import settings
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from . import services

log = logging.getLogger(__name__)


@csrf_exempt
@require_POST
def stripe_webhook(request):
    """Stripe → us. Only signed events are trusted."""
    if not settings.STRIPE_WEBHOOK_SECRET:
        return HttpResponse(status=503)
    try:
        event = stripe.Webhook.construct_event(
            request.body,
            request.META.get('HTTP_STRIPE_SIGNATURE', ''),
            settings.STRIPE_WEBHOOK_SECRET,
        )
    except (ValueError, stripe.SignatureVerificationError):
        log.warning('Rejected Stripe webhook with an invalid signature.')
        return HttpResponse(status=400)

    intent = event['data']['object']
    if event['type'] == 'payment_intent.succeeded':
        services.mark_succeeded(intent['id'])
    elif event['type'] == 'payment_intent.payment_failed':
        services.mark_failed(intent['id'])
    return HttpResponse(status=200)
