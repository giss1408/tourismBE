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
    display_name = graphene.String()
    photo_url = graphene.String()
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
