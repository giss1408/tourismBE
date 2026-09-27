"""Photo and video uploads from the manager app."""
import io
import os
import uuid

from django.conf import settings
from django.core.files.base import ContentFile
from django.db.models import Max
from PIL import Image, ImageOps, UnidentifiedImageError

from .models import Media

IMAGE_TYPES = {'image/jpeg', 'image/png', 'image/webp', 'image/heic', 'image/heif'}
VIDEO_TYPES = {'video/mp4': '.mp4', 'video/quicktime': '.mov', 'video/webm': '.webm'}


class MediaError(Exception):
    pass


def _kind(upload):
    content_type = (upload.content_type or '').lower()
    extension = os.path.splitext(upload.name or '')[1].lower()
    if content_type in IMAGE_TYPES or extension in ('.jpg', '.jpeg', '.png', '.webp'):
        return Media.IMAGE
    if content_type in VIDEO_TYPES or extension in ('.mp4', '.mov', '.webm'):
        return Media.VIDEO
    raise MediaError('Unsupported file type. Use JPEG, PNG or WebP photos, or MP4/MOV videos.')


def _process_image(upload):
    """JPEG at most MEDIA_IMAGE_MAX_SIDE px, correctly rotated, without EXIF."""
    try:
        image = Image.open(upload)
        image = ImageOps.exif_transpose(image)
    except (UnidentifiedImageError, OSError):
        raise MediaError('This photo could not be read.')
    image = image.convert('RGB')
    side = settings.MEDIA_IMAGE_MAX_SIDE
    image.thumbnail((side, side), Image.LANCZOS)
    buffer = io.BytesIO()
    # A fresh save carries no EXIF: GPS position and camera data are dropped.
    image.save(buffer, 'JPEG', quality=85, optimize=True, progressive=True)
    return ContentFile(buffer.getvalue(), name=f'{uuid.uuid4().hex}.jpg')


def save_upload(upload, *, destination=None, tour=None, user=None):
    """Validates and stores [upload] as the last media of its owner."""
    if (destination is None) == (tour is None):
        raise MediaError('Choose a destination or a tour.')
    kind = _kind(upload)
    limit_mb = settings.MEDIA_MAX_IMAGE_MB if kind == Media.IMAGE else settings.MEDIA_MAX_VIDEO_MB
    if upload.size > limit_mb * 1024 * 1024:
        raise MediaError(f'File too large (maximum {limit_mb} MB).')

    if kind == Media.IMAGE:
        content = _process_image(upload)
    else:
        extension = VIDEO_TYPES.get((upload.content_type or '').lower()) \
            or os.path.splitext(upload.name)[1].lower()
        content = upload
        content.name = f'{uuid.uuid4().hex}{extension}'

    siblings = Media.objects.filter(destination=destination, tour=tour)
    position = (siblings.aggregate(last=Max('position'))['last'] or 0) + 1
    media = Media(destination=destination, tour=tour, kind=kind,
                  position=position, uploaded_by=user)
    media.file.save(content.name, content, save=False)
    media.save()
    return media


def delete_media(media):
    media.file.delete(save=False)
    media.delete()
