import graphene
from django.utils.dateparse import parse_datetime
from django.utils import timezone
from .models import AnalyticsEvent, UserProperties


class AnalyticsEventInputType(graphene.InputObjectType):
    name = graphene.String(required=True)
    properties = graphene.JSONString()
    timestamp = graphene.String()


class TrackAnalyticsEvent(graphene.Mutation):
    class Arguments:
        input = AnalyticsEventInputType(required=True)

    ok = graphene.Boolean()

    def mutate(self, info, input):
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

        obj, _ = UserProperties.objects.get_or_create(user=user)
        obj.properties.update(properties or {})
        obj.save()
        return SetAnalyticsUserProperties(ok=True)


# Alias for fallback mutation name
UpdateAnalyticsUserProperties = SetAnalyticsUserProperties


class AnalyticsMutation(graphene.ObjectType):
    track_analytics_event = TrackAnalyticsEvent.Field()
    log_analytics_event = LogAnalyticsEvent.Field()
    set_analytics_user_properties = SetAnalyticsUserProperties.Field()
    update_analytics_user_properties = UpdateAnalyticsUserProperties.Field()
