import json

import graphene
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from apps.accounts.security import ANALYTICS_PER_IP, client_ip

from .models import AnalyticsEvent, UserProperties

MAX_NAME_LENGTH = 100
MAX_PROPERTIES_BYTES = 4096


def _check_properties(properties):
    if len(json.dumps(properties or {})) > MAX_PROPERTIES_BYTES:
        raise Exception('Analytics properties are too large.')


class AnalyticsEventInputType(graphene.InputObjectType):
    name = graphene.String(required=True)
    properties = graphene.JSONString()
    timestamp = graphene.String()


class TrackAnalyticsEvent(graphene.Mutation):
    class Arguments:
        input = AnalyticsEventInputType(required=True)

    ok = graphene.Boolean()

    def mutate(self, info, input):
        ANALYTICS_PER_IP.consume(client_ip(info.context))
        if not input.name or len(input.name) > MAX_NAME_LENGTH:
            raise Exception('Invalid analytics event name.')
        _check_properties(input.properties)
        user = info.context.user if info.context.user.is_authenticated else None
        ts = parse_datetime(input.timestamp) if input.timestamp else timezone.now()

        AnalyticsEvent.objects.create(
            user=user,
            name=input.name,
            properties=input.properties or {},
            timestamp=ts or timezone.now(),
        )
        return TrackAnalyticsEvent(ok=True)


# Alias for fallback mutation name used by the Flutter client
LogAnalyticsEvent = TrackAnalyticsEvent


class SetAnalyticsUserProperties(graphene.Mutation):
    class Arguments:
        properties = graphene.JSONString(required=True)

    ok = graphene.Boolean()

    def mutate(self, info, properties):
        user = info.context.user
        if not user or not user.is_authenticated:
            raise Exception('UNAUTHENTICATED')

        _check_properties(properties)
        obj, _ = UserProperties.objects.get_or_create(user=user)
        obj.properties.update(properties or {})
        _check_properties(obj.properties)
        obj.save()
        return SetAnalyticsUserProperties(ok=True)


# Alias for fallback mutation name
UpdateAnalyticsUserProperties = SetAnalyticsUserProperties


class AnalyticsMutation(graphene.ObjectType):
    track_analytics_event = TrackAnalyticsEvent.Field()
    log_analytics_event = LogAnalyticsEvent.Field()
    set_analytics_user_properties = SetAnalyticsUserProperties.Field()
    update_analytics_user_properties = UpdateAnalyticsUserProperties.Field()
