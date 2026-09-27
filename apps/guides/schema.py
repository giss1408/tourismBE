import graphene

from .models import Guide


class GuideType(graphene.ObjectType):
    id = graphene.ID()
    name = graphene.String()
    bio = graphene.String()
    languages = graphene.List(graphene.String)
    photo_url = graphene.String()
    whatsapp = graphene.String()

    @staticmethod
    def from_model(guide):
        return GuideType(
            id=guide.pk, name=guide.name, bio=guide.bio,
            languages=guide.languages if isinstance(guide.languages, list) else [],
            photo_url=guide.photo_url, whatsapp=guide.whatsapp,
        )


class GuideQuery(graphene.ObjectType):
    guides = graphene.List(GuideType, destination_id=graphene.ID())

    def resolve_guides(self, info, destination_id=None):
        qs = Guide.objects.filter(is_active=True)
        if destination_id:
            qs = qs.filter(destinations__pk=destination_id)
        return [GuideType.from_model(guide) for guide in qs.distinct()]
