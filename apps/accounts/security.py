"""Rate limiting and Firebase ID token verification for the auth mutations."""
import logging

from django.conf import settings
from django.core.cache import cache

log = logging.getLogger(__name__)

TOO_MANY_ATTEMPTS = 'Too many attempts. Please try again in a few minutes.'


class RateLimited(Exception):
    def __init__(self):
        super().__init__(TOO_MANY_ATTEMPTS)


def client_ip(request):
    """The caller's IP, taking NUM_PROXIES trusted reverse proxies into account."""
    if settings.NUM_PROXIES:
        forwarded = [
            ip.strip()
            for ip in request.META.get('HTTP_X_FORWARDED_FOR', '').split(',')
            if ip.strip()
        ]
        if len(forwarded) >= settings.NUM_PROXIES:
            return forwarded[-settings.NUM_PROXIES]
    return request.META.get('REMOTE_ADDR', '')


class RateLimit:
    """At most [limit] hits per [window] seconds for each key."""

    def __init__(self, scope, limit, window):
        self.scope = scope
        self.limit = limit
        self.window = window

    def _key(self, key):
        return f'ratelimit:{self.scope}:{key}'

    def check(self, key):
        """Raises RateLimited when [key] already used up its hits."""
        if cache.get(self._key(key), 0) >= self.limit:
            raise RateLimited()

    def hit(self, key):
        cache_key = self._key(key)
        # add() only sets the expiry on the first hit of the window.
        cache.add(cache_key, 0, self.window)
        try:
            cache.incr(cache_key)
        except ValueError:  # Expired between add() and incr().
            cache.set(cache_key, 1, self.window)

    def consume(self, key):
        """check() then hit(): for limits that count every call."""
        self.check(key)
        self.hit(key)

    def reset(self, key):
        cache.delete(self._key(key))


# Failed sign-ins per account and IP, and all auth calls per IP.
SIGN_IN_FAILURES = RateLimit('sign-in-failures', limit=5, window=15 * 60)
AUTH_CALLS_PER_IP = RateLimit('auth-calls', limit=30, window=15 * 60)
ANALYTICS_PER_IP = RateLimit('analytics', limit=300, window=60)


class FirebaseTokenError(Exception):
    pass


def verify_firebase_id_token(id_token):
    """Claims of a Firebase ID token issued for FIREBASE_PROJECT_ID.

    Checks the signature against Google's public keys, the audience, issuer
    and expiry. Raises FirebaseTokenError when any check fails.
    """
    # Imported lazily: only production social sign-in needs google-auth.
    from google.auth.transport import requests as google_requests
    from google.oauth2 import id_token as google_id_token

    try:
        return google_id_token.verify_firebase_token(
            id_token,
            google_requests.Request(),
            audience=settings.FIREBASE_PROJECT_ID,
        )
    except ValueError as error:
        log.info('Rejected Firebase ID token: %s', error)
        raise FirebaseTokenError('Invalid social sign-in token.') from error
