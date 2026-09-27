import graphene

from apps.accounts.schema import AuthMutation, AuthQuery
from apps.analytics.schema import AnalyticsMutation
from apps.bookings.schema import BookingMutation, BookingQuery
from apps.core.schema import CoreQuery
from apps.destinations.schema import DestinationManagerMutation, DestinationQuery
from apps.guides.schema import GuideQuery
from apps.notifications.schema import NotificationMutation
from apps.payments.schema import PaymentMutation
from apps.reviews.schema import ReviewMutation, ReviewQuery


class Query(AuthQuery, DestinationQuery, BookingQuery, CoreQuery, GuideQuery,
            ReviewQuery, graphene.ObjectType):
    pass


class Mutation(AuthMutation, BookingMutation, AnalyticsMutation, PaymentMutation,
               ReviewMutation, NotificationMutation, DestinationManagerMutation,
               graphene.ObjectType):
    pass


schema = graphene.Schema(query=Query, mutation=Mutation)
