import json
import logging
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError

log = logging.getLogger('tourism.graphql')


class JWTAuthMiddleware:
    """Attach authenticated user to graphql_context from Bearer JWT token."""

    def resolve(self, next, root, info, **kwargs):
        request = info.context

        # Only log + authenticate once per request (at root resolver level)
        if root is None:
            try:
                body = json.loads(request.body.decode('utf-8'))
                op = body.get('operationName', '?')
                variables = body.get('variables', {})
                log.debug('[REQUEST] op=%s variables=%s', op, variables)
            except Exception:
                pass

            auth_header = request.META.get('HTTP_AUTHORIZATION', '')
            if auth_header.lower().startswith('bearer '):
                raw_token = auth_header[7:].strip().encode()
                try:
                    jwt_auth = JWTAuthentication()
                    validated = jwt_auth.get_validated_token(raw_token)
                    user = jwt_auth.get_user(validated)
                    request.user = user
                    log.debug('[AUTH] authenticated as %s', user)
                except (InvalidToken, TokenError) as e:
                    log.warning('[AUTH] token invalid: %s', e)
            else:
                log.debug('[AUTH] anonymous request')

        result = next(root, info, **kwargs)

        # ── Response logging (scalars / lists) ───────────────────────────────
        if root is None:
            try:
                preview = repr(result)[:200]
                log.debug('[RESPONSE] root result preview: %s', preview)
            except Exception:
                pass

        return result
