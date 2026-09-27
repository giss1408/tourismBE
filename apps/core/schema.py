import graphene
from django.conf import settings

from .context import legal_url


class AppSettingsType(graphene.ObjectType):
    """Operator settings the app reads instead of hard-coding them."""
    company_name = graphene.String()
    support_email = graphene.String()
    support_whatsapp = graphene.String()
    service_fee_eur = graphene.Float()
    free_cancellation_days = graphene.Int()
    payments_enabled = graphene.Boolean()
    stripe_publishable_key = graphene.String()
    privacy_policy_url = graphene.String()
    terms_url = graphene.String()


class CoreQuery(graphene.ObjectType):
    app_settings = graphene.Field(AppSettingsType, language=graphene.String())

    def resolve_app_settings(self, info, language='fr'):
        language = language if language in ('fr', 'en', 'de') else 'fr'
        return AppSettingsType(
            company_name=settings.COMPANY_NAME,
            support_email=settings.SUPPORT_EMAIL,
            support_whatsapp=settings.SUPPORT_WHATSAPP,
            service_fee_eur=settings.BOOKING_SERVICE_FEE_EUR,
            free_cancellation_days=settings.FREE_CANCELLATION_DAYS,
            payments_enabled=bool(settings.STRIPE_SECRET_KEY and settings.STRIPE_PUBLISHABLE_KEY),
            stripe_publishable_key=settings.STRIPE_PUBLISHABLE_KEY,
            privacy_policy_url=legal_url('privacy', language),
            terms_url=legal_url('terms', language),
        )
