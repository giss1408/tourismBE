import logging

import graphene
from django.conf import settings
from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.serializers import TokenRefreshSerializer
from rest_framework_simplejwt.tokens import RefreshToken

from .models import AppUser
from .security import (
    AUTH_CALLS_PER_IP,
    SIGN_IN_FAILURES,
    FirebaseTokenError,
    client_ip,
    verify_firebase_id_token,
)

log = logging.getLogger(__name__)

# Social providers the app may report.
SOCIAL_PROVIDERS = {'google', 'facebook', 'apple'}


class AppUserType(graphene.ObjectType):
    uid = graphene.String()
    email = graphene.String()
    display_name = graphene.String()
    photo_url = graphene.String()
    provider = graphene.String()
    created_at = graphene.String()
    language = graphene.String()
    # Managers (staff) can use the manager app.
    is_staff = graphene.Boolean()

    @staticmethod
    def from_model(user):
        return AppUserType(
            uid=str(user.uid),
            email=user.email,
            display_name=user.display_name,
            photo_url=user.photo_url,
            provider=user.provider,
            created_at=user.created_at.isoformat(),
            language=user.language,
            is_staff=user.is_staff,
        )


class AuthPayload(graphene.ObjectType):
    uid = graphene.String()
    email = graphene.String()
    # Flutter mutation requests camelCase 'displayName' / 'photoURL' / 'createdAt'
    # graphene auto-converts snake_case, but 'photo_url' → 'photoUrl' (not 'photoURL'),
    # so we override the GraphQL field name explicitly.
    display_name = graphene.String()
    photo_url = graphene.String(name='photoURL')
    provider = graphene.String()
    created_at = graphene.String()
    access_token = graphene.String()
    refresh_token = graphene.String()


def _auth_payload(user):
    refresh = RefreshToken.for_user(user)
    return AuthPayload(
        uid=str(user.uid),
        email=user.email,
        display_name=user.display_name,
        photo_url=user.photo_url,
        provider=user.provider,
        created_at=user.created_at.isoformat(),
        access_token=str(refresh.access_token),
        refresh_token=str(refresh),
    )


# ─────────── Mutations ───────────

class SignIn(graphene.Mutation):
    class Arguments:
        email = graphene.String(required=True)
        password = graphene.String(required=True)

    Output = AuthPayload

    def mutate(self, info, email, password):
        email = email.lower().strip()
        ip = client_ip(info.context)
        AUTH_CALLS_PER_IP.consume(ip)
        failures_key = f'{ip}:{email}'
        SIGN_IN_FAILURES.check(failures_key)
        user = authenticate(email=email, password=password)
        if user is None:
            SIGN_IN_FAILURES.hit(failures_key)
            raise Exception('Invalid credentials.')
        SIGN_IN_FAILURES.reset(failures_key)
        return _auth_payload(user)


class SignUp(graphene.Mutation):
    class Arguments:
        email = graphene.String(required=True)
        password = graphene.String(required=True)
        display_name = graphene.String(required=True)

    Output = AuthPayload

    def mutate(self, info, email, password, display_name):
        AUTH_CALLS_PER_IP.consume(client_ip(info.context))
        email = email.lower().strip()
        if AppUser.objects.filter(email=email).exists():
            raise Exception('Email already registered.')
        try:
            validate_password(password)
        except ValidationError as e:
            raise Exception(' '.join(e.messages))
        user = AppUser.objects.create_user(
            email=email,
            password=password,
            display_name=display_name.strip(),
        )
        return _auth_payload(user)


class SignOut(graphene.Mutation):
    """Revokes the refresh token; the short-lived access token just expires."""

    class Arguments:
        refresh_token = graphene.String()

    ok = graphene.Boolean()

    def mutate(self, info, refresh_token=None):
        if refresh_token:
            try:
                RefreshToken(refresh_token).blacklist()
            except TokenError:
                pass  # Already expired or revoked: nothing left to revoke.
        return SignOut(ok=True)


class TokenPair(graphene.ObjectType):
    access_token = graphene.String()
    refresh_token = graphene.String()


class RefreshSession(graphene.Mutation):
    """New access token for a refresh token, which is rotated and revoked."""

    class Arguments:
        refresh_token = graphene.String(required=True)

    Output = TokenPair

    def mutate(self, info, refresh_token):
        AUTH_CALLS_PER_IP.consume(client_ip(info.context))
        serializer = TokenRefreshSerializer(data={'refresh': refresh_token})
        try:
            serializer.is_valid(raise_exception=True)
        except Exception:  # Invalid, expired or already-rotated token.
            raise Exception('Session expired. Please sign in again.')
        return TokenPair(
            access_token=serializer.validated_data['access'],
            refresh_token=serializer.validated_data.get('refresh', refresh_token),
        )


class ResetPassword(graphene.Mutation):
    class Arguments:
        email = graphene.String(required=True)

    ok = graphene.Boolean()

    def mutate(self, info, email):
        AUTH_CALLS_PER_IP.consume(client_ip(info.context))
        # In production: send reset email. Here we acknowledge.
        return ResetPassword(ok=True)


# ─────────── Query + Mutation roots ───────────

class SocialSignIn(graphene.Mutation):
    """
    Exchanges a Firebase social sign-in (Google / Facebook) for a backend JWT.

    With FIREBASE_PROJECT_ID set, the app must send the Firebase ID token:
    the uid and email come from its verified claims, never from the client.
    Without it, only development (DEBUG) accepts the client's claims.
    """
    class Arguments:
        id_token = graphene.String()
        uid = graphene.String(required=True)
        email = graphene.String(required=True)
        display_name = graphene.String()
        # Force 'photoURL' (capital URL) to match Flutter DTO field name
        photo_url = graphene.String(name='photoURL')
        provider = graphene.String(required=True)

    Output = AuthPayload

    def mutate(self, info, uid, email, provider,
               id_token=None, display_name='', photo_url='', **kwargs):
        AUTH_CALLS_PER_IP.consume(client_ip(info.context))
        provider = provider if provider in SOCIAL_PROVIDERS else 'social'

        if settings.FIREBASE_PROJECT_ID:
            if not id_token:
                raise Exception('Social sign-in requires an ID token.')
            try:
                claims = verify_firebase_id_token(id_token)
            except FirebaseTokenError as error:
                raise Exception(str(error))
            uid = claims['sub']
            email = claims.get('email') or ''
            # Only a provider-verified email may be linked to an account.
            email_verified = bool(claims.get('email_verified'))
        elif settings.DEBUG:
            log.warning('socialSignIn: trusting client claims (development only).')
            email_verified = True
        else:
            raise Exception('Social sign-in is not available.')

        # Normalise — never store empty string as email
        email = (email or '').lower().strip() or None

        # Find by firebase_uid first, then by a verified email.
        user = AppUser.objects.filter(firebase_uid=uid).first()
        if user is None and email and email_verified:
            user = AppUser.objects.filter(email=email).first()
        if user is None and email and AppUser.objects.filter(email=email).exists():
            raise Exception('An account already uses this email. Sign in with your password.')

        if user is None:
            # New social user — create without a password
            user = AppUser.objects.create_user(
                email=email,  # already None if empty
                password=None,
                display_name=display_name or '',
                photo_url=photo_url or '',
                provider=provider,
                firebase_uid=uid,
            )
        else:
            # Sync latest profile data
            changed = []
            if user.firebase_uid != uid:
                user.firebase_uid = uid
                changed.append('firebase_uid')
            if display_name and user.display_name != display_name:
                user.display_name = display_name
                changed.append('display_name')
            if photo_url and user.photo_url != photo_url:
                user.photo_url = photo_url
                changed.append('photo_url')
            if changed:
                user.save(update_fields=changed)

        return _auth_payload(user)


class UpdatePreferences(graphene.Mutation):
    """Language used for the traveller's emails and notifications."""

    class Arguments:
        language = graphene.String(required=True)

    ok = graphene.Boolean()

    def mutate(self, info, language):
        user = info.context.user
        if not user or not user.is_authenticated:
            raise Exception('UNAUTHENTICATED')
        if language not in ('fr', 'en', 'de'):
            raise Exception('Unsupported language.')
        user.language = language
        user.save(update_fields=['language'])
        return UpdatePreferences(ok=True)


class UpdateProfile(graphene.Mutation):
    class Arguments:
        display_name = graphene.String(required=True)

    Output = AppUserType

    def mutate(self, info, display_name):
        user = info.context.user
        if not user or not user.is_authenticated:
            raise Exception('UNAUTHENTICATED')
        name = display_name.strip()
        if not 1 <= len(name) <= 150:
            raise Exception('Please enter a name of 1 to 150 characters.')
        user.display_name = name
        user.save(update_fields=['display_name'])
        return AppUserType.from_model(user)


class ChangePassword(graphene.Mutation):
    class Arguments:
        current_password = graphene.String(required=True)
        new_password = graphene.String(required=True)

    ok = graphene.Boolean()

    def mutate(self, info, current_password, new_password):
        user = info.context.user
        if not user or not user.is_authenticated:
            raise Exception('UNAUTHENTICATED')
        AUTH_CALLS_PER_IP.consume(client_ip(info.context))
        if not user.check_password(current_password):
            raise Exception('Incorrect password.')
        try:
            validate_password(new_password, user)
        except ValidationError as e:
            raise Exception(' '.join(e.messages))
        user.set_password(new_password)
        user.save(update_fields=['password'])
        return ChangePassword(ok=True)


class DeleteAccount(graphene.Mutation):
    """GDPR erasure: deletes the account and its personal data.

    Bookings stay for accounting, unlinked from the person and without their
    notes. Email accounts must confirm with their password.
    """

    class Arguments:
        password = graphene.String()

    ok = graphene.Boolean()

    def mutate(self, info, password=None):
        user = info.context.user
        if not user or not user.is_authenticated:
            raise Exception('UNAUTHENTICATED')
        AUTH_CALLS_PER_IP.consume(client_ip(info.context))
        if user.has_usable_password() and not user.check_password(password or ''):
            raise Exception('Incorrect password.')
        user.bookings.update(notes='')
        user.analytics_events.all().delete()
        # Revokes every refresh token before the user disappears.
        from rest_framework_simplejwt.token_blacklist.models import OutstandingToken
        for token in OutstandingToken.objects.filter(user=user):
            try:
                RefreshToken(token.token).blacklist()
            except TokenError:
                pass
        user.delete()
        return DeleteAccount(ok=True)


class AuthQuery(graphene.ObjectType):
    me = graphene.Field(AppUserType)

    def resolve_me(self, info):
        user = info.context.user
        if not user or not user.is_authenticated:
            raise Exception('UNAUTHENTICATED')
        return AppUserType.from_model(user)


class AuthMutation(graphene.ObjectType):
    sign_in = SignIn.Field()
    sign_up = SignUp.Field()
    sign_out = SignOut.Field()
    refresh_session = RefreshSession.Field()
    update_preferences = UpdatePreferences.Field()
    update_profile = UpdateProfile.Field()
    change_password = ChangePassword.Field()
    delete_account = DeleteAccount.Field()
    reset_password = ResetPassword.Field()
    social_sign_in = SocialSignIn.Field()
