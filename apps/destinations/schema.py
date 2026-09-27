import json as json_lib

import graphene
from django.db import transaction
from django.db.models import Prefetch, Q
from graphene_django import DjangoObjectType

from .media import delete_media
from .models import Destination, Media, Tour, public_url


def _json_list(value):
    if isinstance(value, list):
        return value
    if isinstance(value, str):
        try:
            parsed = json_lib.loads(value)
            return parsed if isinstance(parsed, list) else []
        except (ValueError, TypeError):
            return []
    return []


def _is_manager(info):
    user = info.context.user
    return bool(user and user.is_authenticated and user.is_staff)


def _require_manager(info):
    if not _is_manager(info):
        raise Exception('Manager access required.')
    return info.context.user


class MediaType(graphene.ObjectType):
    id = graphene.ID()
    kind = graphene.String()
    url = graphene.String()
    position = graphene.Int()

    @staticmethod
    def from_model(media):
        return MediaType(id=media.pk, kind=media.kind,
                         url=public_url(media.file), position=media.position)


class TourType(graphene.ObjectType):
    id = graphene.ID()
    destination_id = graphene.ID()
    title = graphene.String()
    description = graphene.String()
    duration_hours = graphene.Float()
    price = graphene.Float()
    max_group_size = graphene.Int()
    languages = graphene.List(graphene.String)
    guide_id = graphene.ID()
    guide_name = graphene.String()
    is_published = graphene.Boolean()
    position = graphene.Int()
    images = graphene.List(graphene.String)
    videos = graphene.List(graphene.String)
    media = graphene.List(MediaType)

    @staticmethod
    def from_model(tour):
        return TourType(
            id=tour.pk, destination_id=tour.destination_id, title=tour.title,
            description=tour.description, duration_hours=tour.duration_hours,
            price=tour.price, max_group_size=tour.max_group_size,
            languages=_json_list(tour.languages),
            guide_id=tour.guide_id, guide_name=tour.guide.name if tour.guide else '',
            is_published=tour.is_published, position=tour.position,
            images=tour.image_urls(), videos=tour.video_urls(),
            media=[MediaType.from_model(m) for m in tour.media.all()],
        )


class DestinationType(DjangoObjectType):
    class Meta:
        model = Destination
        fields = (
            'id', 'name', 'description', 'location', 'rating', 'price',
            'is_featured', 'category', 'available_spots', 'discount',
            'latitude', 'longitude', 'review_count', 'is_published',
        )

    images = graphene.List(graphene.String)
    videos = graphene.List(graphene.String)
    activities = graphene.List(graphene.String)
    tours = graphene.List(TourType)
    # Manager app: uploaded photos and videos with their ids, in order.
    media = graphene.List(MediaType)

    def resolve_images(self, info):
        return self.image_urls()

    def resolve_videos(self, info):
        return self.video_urls()

    def resolve_activities(self, info):
        return _json_list(self.activities)

    def resolve_tours(self, info):
        tours = self.tours.all()
        if not _is_manager(info):
            tours = [tour for tour in tours if tour.is_published]
        return [TourType.from_model(tour) for tour in tours]

    def resolve_media(self, info):
        _require_manager(info)
        return [MediaType.from_model(m) for m in self.media.all()]


def _destinations():
    return Destination.objects.prefetch_related(
        'media',
        Prefetch('tours', queryset=Tour.objects.select_related('guide')
                 .prefetch_related('media')),
    )


def _filtered(qs, search=None, category=None, sort_by=None, sort_direction=None,
              page=None, page_size=None):
    if search and search.strip():
        term = search.strip()
        qs = qs.filter(Q(name__icontains=term) | Q(location__icontains=term)
                       | Q(description__icontains=term))
    if category and category.strip():
        qs = qs.filter(category__iexact=category.strip())
    sort_field = sort_by if sort_by in {'rating', 'price', 'name', 'created_at'} else 'rating'
    prefix = '-' if (sort_direction or 'desc').lower() == 'desc' else ''
    qs = qs.order_by(f'{prefix}{sort_field}')
    page = max(1, page or 1)
    page_size = min(100, max(1, page_size or 20))
    offset = (page - 1) * page_size
    return qs[offset: offset + page_size]


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

    # Manager app: drafts included.
    manager_destinations = graphene.List(
        DestinationType, search=graphene.String(), page=graphene.Int(),
        page_size=graphene.Int())
    manager_destination = graphene.Field(DestinationType, id=graphene.ID(required=True))

    def resolve_destinations(self, info, **options):
        return _filtered(_destinations().filter(is_published=True), **options)

    def resolve_destination(self, info, id):
        destination = _destinations().filter(pk=id, is_published=True).first()
        if destination is None:
            raise Exception(f'Destination {id} not found.')
        return destination

    def resolve_manager_destinations(self, info, search=None, page=None, page_size=None):
        _require_manager(info)
        qs = _destinations()
        if search and search.strip():
            term = search.strip()
            qs = qs.filter(Q(name__icontains=term) | Q(location__icontains=term))
        page = max(1, page or 1)
        page_size = min(100, max(1, page_size or 50))
        offset = (page - 1) * page_size
        return qs.order_by('-updated_at')[offset: offset + page_size]

    def resolve_manager_destination(self, info, id):
        _require_manager(info)
        return _destinations().filter(pk=id).first()


# ─────────── Manager mutations ───────────

class DestinationInput(graphene.InputObjectType):
    name = graphene.String(required=True)
    description = graphene.String()
    location = graphene.String()
    category = graphene.String()
    price = graphene.Float()
    discount = graphene.Float()
    available_spots = graphene.Int()
    activities = graphene.List(graphene.String)
    is_featured = graphene.Boolean()
    is_published = graphene.Boolean()
    latitude = graphene.Float()
    longitude = graphene.Float()


def _validate_destination(data):
    if not (data.get('name') or '').strip():
        raise Exception('The name is required.')
    if (data.get('price') or 0) < 0:
        raise Exception('The price cannot be negative.')
    if not 0 <= (data.get('discount') or 0) < 1:
        raise Exception('The discount must be between 0 and 99%.')
    for key in ('latitude', 'longitude'):
        value = data.get(key)
        limit = 90 if key == 'latitude' else 180
        if value is not None and not -limit <= value <= limit:
            raise Exception('Invalid coordinates.')


class SaveDestination(graphene.Mutation):
    """Creates (without id) or updates a destination."""

    class Arguments:
        id = graphene.ID()
        input = DestinationInput(required=True)

    Output = DestinationType

    def mutate(self, info, input, id=None):
        _require_manager(info)
        data = {key: value for key, value in input.items()}
        _validate_destination(data)
        if 'activities' in data:
            data['activities'] = [a.strip() for a in data['activities'] or [] if a.strip()]
        data['name'] = data['name'].strip()
        if id:
            destination = Destination.objects.filter(pk=id).first()
            if destination is None:
                raise Exception('Destination not found.')
        else:
            destination = Destination(description='', location='', category='')
            data.setdefault('is_published', False)
        for key, value in data.items():
            setattr(destination, key, value)
        destination.save()
        return _destinations().get(pk=destination.pk)


class DeleteDestination(graphene.Mutation):
    class Arguments:
        id = graphene.ID(required=True)

    ok = graphene.Boolean()

    def mutate(self, info, id):
        _require_manager(info)
        destination = Destination.objects.filter(pk=id).first()
        if destination is not None:
            with transaction.atomic():
                for media in Media.objects.filter(Q(destination=destination)
                                                  | Q(tour__destination=destination)):
                    delete_media(media)
                destination.delete()
        return DeleteDestination(ok=True)


class TourInput(graphene.InputObjectType):
    destination_id = graphene.ID()
    title = graphene.String(required=True)
    description = graphene.String()
    duration_hours = graphene.Float()
    price = graphene.Float()
    max_group_size = graphene.Int()
    languages = graphene.List(graphene.String)
    guide_id = graphene.ID()
    is_published = graphene.Boolean()


class SaveTour(graphene.Mutation):
    """Creates (without id, with destinationId) or updates a tour."""

    class Arguments:
        id = graphene.ID()
        input = TourInput(required=True)

    Output = TourType

    def mutate(self, info, input, id=None):
        _require_manager(info)
        data = {key: value for key, value in input.items()}
        if not (data.get('title') or '').strip():
            raise Exception('The title is required.')
        if (data.get('price') or 0) < 0 or (data.get('duration_hours') or 1) <= 0:
            raise Exception('Invalid price or duration.')
        if 'languages' in data:
            data['languages'] = [code for code in data['languages'] or []
                                 if code in ('fr', 'en', 'de', 'it', 'es')]
        destination_id = data.pop('destination_id', None)
        guide_id = data.pop('guide_id', None)
        if id:
            tour = Tour.objects.filter(pk=id).first()
            if tour is None:
                raise Exception('Tour not found.')
        else:
            destination = Destination.objects.filter(pk=destination_id).first()
            if destination is None:
                raise Exception('Unknown destination.')
            tour = Tour(destination=destination,
                        position=destination.tours.count() + 1)
        for key, value in data.items():
            setattr(tour, key, value.strip() if isinstance(value, str) else value)
        if 'guide_id' in input:
            tour.guide_id = guide_id or None
        tour.save()
        return TourType.from_model(Tour.objects.select_related('guide').get(pk=tour.pk))


class DeleteTour(graphene.Mutation):
    class Arguments:
        id = graphene.ID(required=True)

    ok = graphene.Boolean()

    def mutate(self, info, id):
        _require_manager(info)
        tour = Tour.objects.filter(pk=id).first()
        if tour is not None:
            with transaction.atomic():
                for media in tour.media.all():
                    delete_media(media)
                tour.delete()
        return DeleteTour(ok=True)


class ReorderMedia(graphene.Mutation):
    """Sets the order of a gallery; the first photo becomes the cover."""

    class Arguments:
        ids = graphene.List(graphene.ID, required=True)

    ok = graphene.Boolean()

    def mutate(self, info, ids):
        _require_manager(info)
        items = {str(m.pk): m for m in Media.objects.filter(pk__in=ids)}
        owners = {(m.destination_id, m.tour_id) for m in items.values()}
        if len(owners) > 1:
            raise Exception('These files belong to different galleries.')
        with transaction.atomic():
            for position, media_id in enumerate(ids, start=1):
                media = items.get(str(media_id))
                if media is not None and media.position != position:
                    media.position = position
                    media.save(update_fields=['position'])
        return ReorderMedia(ok=True)


class DeleteMedia(graphene.Mutation):
    class Arguments:
        id = graphene.ID(required=True)

    ok = graphene.Boolean()

    def mutate(self, info, id):
        _require_manager(info)
        media = Media.objects.filter(pk=id).first()
        if media is not None:
            delete_media(media)
        return DeleteMedia(ok=True)


class DestinationManagerMutation(graphene.ObjectType):
    save_destination = SaveDestination.Field()
    delete_destination = DeleteDestination.Field()
    save_tour = SaveTour.Field()
    delete_tour = DeleteTour.Field()
    reorder_media = ReorderMedia.Field()
    delete_media = DeleteMedia.Field()
