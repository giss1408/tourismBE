import graphene

from .models import DeviceToken


def _user(info):
    user = info.context.user
    if not user or not user.is_authenticated:
        raise Exception('UNAUTHENTICATED')
    return user


class RegisterDevice(graphene.Mutation):
    class Arguments:
        token = graphene.String(required=True)
        platform = graphene.String()

    ok = graphene.Boolean()

    def mutate(self, info, token, platform=''):
        user = _user(info)
        # A token moves to whoever signed in last on that device.
        DeviceToken.objects.update_or_create(
            token=token[:512], defaults={'user': user, 'platform': (platform or '')[:20]})
        return RegisterDevice(ok=True)


class UnregisterDevice(graphene.Mutation):
    class Arguments:
        token = graphene.String(required=True)

    ok = graphene.Boolean()

    def mutate(self, info, token):
        DeviceToken.objects.filter(user=_user(info), token=token).delete()
        return UnregisterDevice(ok=True)


class NotificationMutation(graphene.ObjectType):
    register_device = RegisterDevice.Field()
    unregister_device = UnregisterDevice.Field()
