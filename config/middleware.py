import json
import logging

from django.contrib.auth.models import AnonymousUser
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError

log = logging.getLogger('tourism.graphql')

def _authenticate(request):
    """Sets request.user from the bearer token, and only from it.

    The session user is dropped on purpose: /graphql/ is CSRF-exempt, so
    trusting the admin session cookie would let another site act as a
    signed-in staff member.
    """
    request.user = AnonymousUser()
    auth_header = request.META.get('HTTP_AUTHORIZATION', '')
    if not auth_header.lower().startswith('bearer '):
        return
    raw_token = auth_header[7:].strip().encode()
    try:
        jwt_auth = JWTAuthentication()
        validated = jwt_auth.get_validated_token(raw_token)
        request.user = jwt_auth.get_user(validated)
    except (InvalidToken, TokenError) as error:
        log.info('[AUTH] rejected token: %s', error)


class JWTAuthMiddleware:
    """Graphene middleware: authenticates each request once, by bearer JWT."""

    def resolve(self, next, root, info, **kwargs):
        request = info.context
        if root is None and not getattr(request, '_jwt_checked', False):
            request._jwt_checked = True
            _authenticate(request)
            if log.isEnabledFor(logging.DEBUG):
                try:
                    body = json.loads(request.body.decode('utf-8'))
                    # Variable names only: values may hold passwords or
                    # tokens, under any name a client chooses.
                    log.debug('[REQUEST] op=%s user=%s variables=%s',
                              body.get('operationName', '?'),
                              getattr(request.user, 'pk', None),
                              sorted((body.get('variables') or {}).keys()))
                except (ValueError, UnicodeDecodeError):
                    pass
        return next(root, info, **kwargs)
