from django.conf import settings
from django.contrib import admin
from django.urls import path
from django.views.decorators.csrf import csrf_exempt
from graphene_django.views import GraphQLView

from apps.core.views import healthz, legal
from apps.destinations.views import upload_media
from apps.payments.views import stripe_webhook

urlpatterns = [
    path('admin/', admin.site.urls),
    # CSRF is safe to skip: the API ignores session cookies and only trusts
    # bearer tokens (see config.middleware). The GraphiQL explorer is
    # development-only.
    path('graphql/', csrf_exempt(GraphQLView.as_view(graphiql=settings.DEBUG))),
    path('healthz/', healthz),
    path('legal/<slug:document>/', legal),
    path('payments/stripe/webhook/', stripe_webhook),
    path('manager/media/', upload_media),
]

if settings.DEBUG:
    # Production serves uploads from Caddy (deploy/Caddyfile).
    from django.conf.urls.static import static

    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
