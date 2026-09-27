"""Transactional emails, written in the traveller's language."""
import logging

from django.conf import settings
from django.core.mail import send_mail

log = logging.getLogger(__name__)

# {kind: {language: (subject, body)}}. Body placeholders: name, reference,
# destination, check_in, check_out, total, company, support, days.
MESSAGES = {
    'booking_received': {
        'fr': ('Demande de réservation reçue – {reference}',
               'Bonjour {name},\n\nNous avons bien reçu votre demande de réservation '
               'pour {destination} du {check_in} au {check_out} (total : {total}).\n'
               'Nous vérifions les disponibilités et revenons vers vous très vite.\n\n'
               'Annulation gratuite jusqu’à {days} jours avant l’arrivée.\n\n'
               'Référence : {reference}\n\n{company}\n{support}'),
        'en': ('Booking request received – {reference}',
               'Hello {name},\n\nWe have received your booking request for '
               '{destination} from {check_in} to {check_out} (total: {total}).\n'
               'We are checking availability and will get back to you shortly.\n\n'
               'Free cancellation up to {days} days before arrival.\n\n'
               'Reference: {reference}\n\n{company}\n{support}'),
        'de': ('Buchungsanfrage erhalten – {reference}',
               'Hallo {name},\n\nwir haben Ihre Buchungsanfrage für {destination} '
               'vom {check_in} bis {check_out} erhalten (Gesamt: {total}).\n'
               'Wir prüfen die Verfügbarkeit und melden uns in Kürze.\n\n'
               'Kostenlose Stornierung bis {days} Tage vor Anreise.\n\n'
               'Referenz: {reference}\n\n{company}\n{support}'),
    },
    'booking_confirmed': {
        'fr': ('Réservation confirmée – {reference}',
               'Bonjour {name},\n\nVotre réservation pour {destination} du {check_in} '
               'au {check_out} est confirmée. Akwaba, bienvenue en Côte d’Ivoire !\n\n'
               'Référence : {reference}\nTotal : {total}\n\n{company}\n{support}'),
        'en': ('Booking confirmed – {reference}',
               'Hello {name},\n\nYour booking for {destination} from {check_in} to '
               '{check_out} is confirmed. Akwaba, welcome to Côte d’Ivoire!\n\n'
               'Reference: {reference}\nTotal: {total}\n\n{company}\n{support}'),
        'de': ('Buchung bestätigt – {reference}',
               'Hallo {name},\n\nIhre Buchung für {destination} vom {check_in} bis '
               '{check_out} ist bestätigt. Akwaba, willkommen an der Elfenbeinküste!\n\n'
               'Referenz: {reference}\nGesamt: {total}\n\n{company}\n{support}'),
    },
    'booking_cancelled': {
        'fr': ('Réservation annulée – {reference}',
               'Bonjour {name},\n\nVotre réservation {reference} pour {destination} '
               'a été annulée. Si un paiement a été remboursé, il apparaîtra sous '
               '5 à 10 jours ouvrés.\n\n{company}\n{support}'),
        'en': ('Booking cancelled – {reference}',
               'Hello {name},\n\nYour booking {reference} for {destination} has been '
               'cancelled. Any refund will appear within 5 to 10 business days.\n\n'
               '{company}\n{support}'),
        'de': ('Buchung storniert – {reference}',
               'Hallo {name},\n\nIhre Buchung {reference} für {destination} wurde '
               'storniert. Eine Erstattung erscheint innerhalb von 5 bis 10 '
               'Werktagen.\n\n{company}\n{support}'),
    },
}


def _format_eur(amount, language):
    text = f'{amount:,.2f}'
    if language in ('fr', 'de'):
        # 1,234.50 -> 1 234,50 (fr) / 1.234,50 (de)
        thousands = ' ' if language == 'fr' else '.'
        text = text.replace(',', '§').replace('.', ',').replace('§', thousands)
        return f'{text} €'
    return f'€{text}'


def send_booking_email(booking, kind):
    """Emails the booking's traveller; failures are logged, never raised."""
    user = booking.user
    if user is None or not user.email:
        return False
    language = getattr(user, 'language', 'fr') or 'fr'
    subject, body = MESSAGES[kind].get(language, MESSAGES[kind]['fr'])
    values = {
        'name': user.display_name or user.email,
        'reference': booking.reference,
        'destination': booking.destination_name,
        'check_in': booking.check_in_date.strftime('%d/%m/%Y'),
        'check_out': booking.check_out_date.strftime('%d/%m/%Y'),
        'total': _format_eur(booking.total_price, language),
        'company': settings.COMPANY_NAME,
        'support': settings.SUPPORT_EMAIL,
        'days': settings.FREE_CANCELLATION_DAYS,
    }
    try:
        send_mail(subject.format(**values), body.format(**values),
                  settings.DEFAULT_FROM_EMAIL, [user.email])
        return True
    except Exception:
        log.exception('Could not send %s email for booking %s', kind, booking.pk)
        return False
