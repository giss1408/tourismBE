import graphene
from apps.accounts.schema import AuthQuery, AuthMutation
from apps.destinations.schema import DestinationQuery
from apps.bookings.schema import BookingQuery, BookingMutation
from apps.analytics.schema import AnalyticsMutation


class Query(AuthQuery, DestinationQuery, BookingQuery, graphene.ObjectType):
    pass


class Mutation(AuthMutation, BookingMutation, AnalyticsMutation, graphene.ObjectType):
    pass


schema = graphene.Schema(query=Query, mutation=Mutation)
