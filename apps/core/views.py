from django.conf import settings
from django.db import connection
from django.http import Http404, JsonResponse
from django.shortcuts import render

LEGAL_LANGUAGES = ('fr', 'en', 'de')
LEGAL_DOCUMENTS = ('privacy', 'terms')


def healthz(request):
    """Liveness + database check for the load balancer and uptime monitor."""
    try:
        with connection.cursor() as cursor:
            cursor.execute('SELECT 1')
    except Exception:
        return JsonResponse({'status': 'error', 'database': 'unavailable'}, status=503)
    return JsonResponse({'status': 'ok'})


def legal(request, document):
    """Privacy policy and terms of sale, in ?lang=fr|en|de (French default)."""
    if document not in LEGAL_DOCUMENTS:
        raise Http404
    language = request.GET.get('lang', 'fr')
    if language not in LEGAL_LANGUAGES:
        language = 'fr'
    return render(request, f'legal/{document}_{language}.html', {
        'languages': LEGAL_LANGUAGES,
        'language': language,
        'document': document,
        'company': settings.COMPANY_NAME,
        'support_email': settings.SUPPORT_EMAIL,
        'free_cancellation_days': settings.FREE_CANCELLATION_DAYS,
        'service_fee': settings.BOOKING_SERVICE_FEE_EUR,
    })
