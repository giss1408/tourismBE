import graphene

from apps.bookings.models import Booking
from apps.destinations.models import Destination

from .models import Review


class ReviewType(graphene.ObjectType):
    id = graphene.ID()
    rating = graphene.Int()
    comment = graphene.String()
    # First name only: reviews are public.
    author_name = graphene.String()
    created_at = graphene.String()
    is_mine = graphene.Boolean()

    @staticmethod
    def from_model(review, viewer=None):
        name = (review.user.display_name or '').split(' ')[0] or 'Voyageur'
        return ReviewType(
            id=review.pk,
            rating=review.rating,
            comment=review.comment,
            author_name=name,
            created_at=review.created_at.isoformat(),
            is_mine=bool(viewer and viewer.is_authenticated and viewer.pk == review.user_id),
        )


class ReviewQuery(graphene.ObjectType):
    reviews = graphene.List(
        ReviewType,
        destination_id=graphene.ID(required=True),
        page=graphene.Int(),
        page_size=graphene.Int(),
    )

    def resolve_reviews(self, info, destination_id, page=None, page_size=None):
        page = max(1, page or 1)
        page_size = min(50, max(1, page_size or 10))
        offset = (page - 1) * page_size
        qs = Review.objects.filter(destination_id=destination_id, is_visible=True) \
            .select_related('user')[offset: offset + page_size]
        return [ReviewType.from_model(review, info.context.user) for review in qs]


class SubmitReview(graphene.Mutation):
    """Adds or updates the traveller's review of a destination they booked."""

    class Arguments:
        destination_id = graphene.ID(required=True)
        rating = graphene.Int(required=True)
        comment = graphene.String()

    Output = ReviewType

    def mutate(self, info, destination_id, rating, comment=''):
        user = info.context.user
        if not user or not user.is_authenticated:
            raise Exception('UNAUTHENTICATED')
        if not 1 <= rating <= 5:
            raise Exception('The rating must be between 1 and 5.')
        destination = Destination.objects.filter(pk=destination_id).first()
        if destination is None:
            raise Exception('Unknown destination.')
        # Verified travellers only: a confirmed booking of this destination.
        if not Booking.objects.filter(
                user=user, destination_id=str(destination.pk),
                status=Booking.STATUS_CONFIRMED).exists():
            raise Exception('Only travellers who booked this destination can review it.')
        review, _ = Review.objects.update_or_create(
            destination=destination, user=user,
            defaults={'rating': rating, 'comment': (comment or '').strip()[:2000]},
        )
        return ReviewType.from_model(review, user)


class ReviewMutation(graphene.ObjectType):
    submit_review = SubmitReview.Field()
