import graphene
from graphene_django import DjangoObjectType
from .models import Destination
from django.db.models import Q


class DestinationType(DjangoObjectType):
    class Meta:
        model = Destination
        fields = (
            'id', 'name', 'description', 'location', 'rating', 'price',
            'images', 'activities', 'is_featured', 'category',
            'available_spots', 'discount', 'latitude', 'longitude',
        )


class DestinationQuery(graphene.ObjectType):
    destinations = graphene.List(
        DestinationType,
        search=graphene.String(),
        category=graphene.String(),
        sort_by=graphene.String(),
        sort_direction=graphene.String(),
        page=graphene.Int(),
        page_size=graphene.Int(),
    )
    destination = graphene.Field(DestinationType, id=graphene.ID(required=True))

    def resolve_destinations(
        self, info,
        search=None, category=None,
        sort_by=None, sort_direction=None,
        page=None, page_size=None,
    ):
        qs = Destination.objects.all()

        if search and search.strip():
            term = search.strip()
            qs = qs.filter(
                Q(name__icontains=term) |
                Q(location__icontains=term) |
                Q(description__icontains=term)
            )

        if category and category.strip():
            qs = qs.filter(category__iexact=category.strip())

        # Sorting
        sort_field = sort_by or 'rating'
        allowed_sort = {'rating', 'price', 'name', 'created_at'}
        if sort_field not in allowed_sort:
            sort_field = 'rating'
        prefix = '-' if (sort_direction or 'desc').lower() == 'desc' else ''
        qs = qs.order_by(f'{prefix}{sort_field}')

        # Pagination
        page = max(1, page or 1)
        page_size = min(100, max(1, page_size or 20))
        offset = (page - 1) * page_size
        return qs[offset: offset + page_size]

    def resolve_destination(self, info, id):
        try:
            return Destination.objects.get(pk=id)
        except Destination.DoesNotExist:
            raise Exception(f'Destination {id} not found.')
