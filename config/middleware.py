from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError


class JWTAuthMiddleware:
    """Attach authenticated user to graphql_context from Bearer JWT token."""

    def resolve(self, next, root, info, **kwargs):
        request = info.context
        auth_header = request.META.get('HTTP_AUTHORIZATION', '')

        if auth_header.lower().startswith('bearer '):
            raw_token = auth_header[7:].strip().encode()
            try:
                jwt_auth = JWTAuthentication()
                validated = jwt_auth.get_validated_token(raw_token)
                user = jwt_auth.get_user(validated)
                request.user = user
            except (InvalidToken, TokenError):
                pass

        return next(root, info, **kwargs)
