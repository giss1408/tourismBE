import graphene
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from .models import AppUser


class AppUserType(graphene.ObjectType):
    uid = graphene.String()
    email = graphene.String()
    display_name = graphene.String()
    photo_url = graphene.String()
    provider = graphene.String()
    created_at = graphene.String()

    @staticmethod
    def from_model(user):
        return AppUserType(
            uid=str(user.uid),
            email=user.email,
            display_name=user.display_name,
            photo_url=user.photo_url,
            provider=user.provider,
            created_at=user.created_at.isoformat(),
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
        user = authenticate(email=email.lower().strip(), password=password)
        if user is None:
            raise Exception('Invalid credentials.')
        return _auth_payload(user)


class SignUp(graphene.Mutation):
    class Arguments:
        email = graphene.String(required=True)
        password = graphene.String(required=True)
        display_name = graphene.String(required=True)

    Output = AuthPayload

    def mutate(self, info, email, password, display_name):
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
    ok = graphene.Boolean()

    def mutate(self, info):
        # Stateless JWT — client discards its token
        return SignOut(ok=True)


class ResetPassword(graphene.Mutation):
    class Arguments:
        email = graphene.String(required=True)

    ok = graphene.Boolean()

    def mutate(self, info, email):
        # In production: send reset email. Here we acknowledge.
        return ResetPassword(ok=True)


# ─────────── Query + Mutation roots ───────────

class SocialSignIn(graphene.Mutation):
    """
    Accepts Firebase social-auth user claims and returns a backend JWT.
    The mobile app performs the OAuth flow (Google / Facebook) via Firebase,
    then sends the resulting uid/email here so the backend can create or
    update the matching AppUser and issue its own JWT.

    NOTE: For production, verify the Firebase ID token via firebase-admin SDK.
          For the current dev setup we trust the claims directly.
    """
    class Arguments:
        uid = graphene.String(required=True)
        email = graphene.String(required=True)
        display_name = graphene.String()
        # Force 'photoURL' (capital URL) to match Flutter DTO field name
        photo_url = graphene.String(name='photoURL')
        provider = graphene.String(required=True)

    Output = AuthPayload

    def mutate(self, info, uid, email, provider,
               display_name='', photo_url='', **kwargs):
        # Normalise — never store empty string as email
        email = (email or '').lower().strip() or None

        # Find by firebase_uid first, then fall back to email only if non-null
        user = AppUser.objects.filter(firebase_uid=uid).first()
        if user is None and email:
            user = AppUser.objects.filter(email=email).first()

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
            changed = False
            if user.firebase_uid != uid:
                user.firebase_uid = uid
                changed = True
            if display_name and user.display_name != display_name:
                user.display_name = display_name
                changed = True
            if photo_url and user.photo_url != photo_url:
                user.photo_url = photo_url
                changed = True
            if changed:
                user.save(update_fields=[f for f in
                          ['firebase_uid', 'display_name', 'photo_url']
                          if changed])

        return _auth_payload(user)


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
    reset_password = ResetPassword.Field()
    social_sign_in = SocialSignIn.Field()
