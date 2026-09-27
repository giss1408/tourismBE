"""Push notifications through Firebase Cloud Messaging (HTTP v1 API).

Disabled (every call is a no-op) until FCM_CREDENTIALS_FILE points to a
Firebase service-account key.
"""
import json
import logging

import requests
from django.conf import settings

from .models import DeviceToken

log = logging.getLogger(__name__)

FCM_SCOPE = 'https://www.googleapis.com/auth/firebase.messaging'

MESSAGES = {
    'booking_confirmed': {
        'fr': ('Réservation confirmée', 'Votre séjour à {destination} est confirmé. Akwaba !'),
        'en': ('Booking confirmed', 'Your stay at {destination} is confirmed. Akwaba!'),
        'de': ('Buchung bestätigt', 'Ihr Aufenthalt in {destination} ist bestätigt. Akwaba!'),
    },
    'trip_reminder': {
        'fr': ('C’est demain !', 'Votre séjour à {destination} commence demain. Bon voyage !'),
        'en': ('It’s tomorrow!', 'Your stay at {destination} starts tomorrow. Have a great trip!'),
        'de': ('Morgen geht’s los!', 'Ihr Aufenthalt in {destination} beginnt morgen. Gute Reise!'),
    },
}

_credentials = None


def push_enabled():
    return bool(settings.FCM_CREDENTIALS_FILE)


def _access_token_and_project():
    global _credentials
    from google.auth.transport.requests import Request
    from google.oauth2 import service_account

    if _credentials is None:
        _credentials = service_account.Credentials.from_service_account_file(
            settings.FCM_CREDENTIALS_FILE, scopes=[FCM_SCOPE])
    if not _credentials.valid:
        _credentials.refresh(Request())
    return _credentials.token, _credentials.project_id


def send_to_user(user, title, body, data=None):
    """Sends to every device of [user]; drops tokens FCM no longer knows."""
    if not push_enabled() or user is None:
        return 0
    try:
        access_token, project_id = _access_token_and_project()
    except Exception:
        log.exception('FCM credentials could not be loaded.')
        return 0
    url = f'https://fcm.googleapis.com/v1/projects/{project_id}/messages:send'
    sent = 0
    for device in DeviceToken.objects.filter(user=user):
        message = {'message': {
            'token': device.token,
            'notification': {'title': title, 'body': body},
            'data': {key: str(value) for key, value in (data or {}).items()},
        }}
        try:
            response = requests.post(
                url, data=json.dumps(message), timeout=10,
                headers={'Authorization': f'Bearer {access_token}',
                         'Content-Type': 'application/json'})
        except requests.RequestException:
            log.warning('FCM request failed for device %s', device.pk)
            continue
        if response.status_code in (404, 410) or 'UNREGISTERED' in response.text:
            device.delete()  # App uninstalled or token rotated.
        elif response.ok:
            sent += 1
        else:
            log.warning('FCM error %s: %s', response.status_code, response.text[:200])
    return sent


def notify_booking(booking, kind):
    user = booking.user
    if user is None:
        return 0
    language = getattr(user, 'language', 'fr') or 'fr'
    title, body = MESSAGES[kind].get(language, MESSAGES[kind]['fr'])
    return send_to_user(
        user, title, body.format(destination=booking.destination_name),
        data={'type': kind, 'reference': booking.reference})
