from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError

from .media import MediaError, save_upload
from .models import Destination, Tour, public_url


def _staff_user(request):
    header = request.META.get('HTTP_AUTHORIZATION', '')
    if not header.lower().startswith('bearer '):
        return None
    try:
        auth = JWTAuthentication()
        user = auth.get_user(auth.get_validated_token(header[7:].strip().encode()))
    except (InvalidToken, TokenError):
        return None
    return user if user.is_active and user.is_staff else None


@csrf_exempt
@require_POST
def upload_media(request):
    """Manager app: multipart `file` + `destination_id` or `tour_id`."""
    user = _staff_user(request)
    if user is None:
        return JsonResponse({'error': 'Manager access required.'}, status=403)
    upload = request.FILES.get('file')
    if upload is None:
        return JsonResponse({'error': 'No file received.'}, status=400)
    destination = tour = None
    if request.POST.get('destination_id'):
        destination = Destination.objects.filter(pk=request.POST['destination_id']).first()
    if request.POST.get('tour_id'):
        tour = Tour.objects.filter(pk=request.POST['tour_id']).first()
    if destination is None and tour is None:
        return JsonResponse({'error': 'Unknown destination or tour.'}, status=404)
    try:
        media = save_upload(upload, destination=destination, tour=tour, user=user)
    except MediaError as error:
        return JsonResponse({'error': str(error)}, status=400)
    return JsonResponse({
        'id': str(media.pk),
        'kind': media.kind,
        'url': public_url(media.file),
        'position': media.position,
    }, status=201)
