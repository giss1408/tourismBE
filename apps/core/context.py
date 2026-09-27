from django.conf import settings


def legal_url(document, language='fr'):
    """Public URL of a legal page ('privacy' or 'terms')."""
    return f'{settings.PUBLIC_BASE_URL.rstrip("/")}/legal/{document}/?lang={language}'
