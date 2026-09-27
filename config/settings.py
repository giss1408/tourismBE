"""
Django settings for tourism backend.
"""
import sys
from datetime import timedelta
from pathlib import Path

import dj_database_url
from decouple import Csv, config
from django.core.exceptions import ImproperlyConfigured

BASE_DIR = Path(__file__).resolve().parent.parent

# dev, staging or production: labels logs and error reports.
APP_ENV = config('APP_ENV', default='development')
TESTING = 'test' in sys.argv

# Production is the default: development must opt in with DEBUG=True.
DEBUG = config('DEBUG', default=False, cast=bool)

SECRET_KEY = config('SECRET_KEY', default='')
if not SECRET_KEY:
    if not DEBUG:
        raise ImproperlyConfigured('SECRET_KEY must be set when DEBUG is off.')
    SECRET_KEY = 'dev-only-insecure-secret-key'

ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='localhost,127.0.0.1', cast=Csv())

# Origins allowed to post forms to the admin (e.g. https://api.example.com).
CSRF_TRUSTED_ORIGINS = config('CSRF_TRUSTED_ORIGINS', default='', cast=Csv())

# Render sets these on every service: its own *.onrender.com address works
# without listing it (a custom domain still goes in ALLOWED_HOSTS).
RENDER_EXTERNAL_HOSTNAME = config('RENDER_EXTERNAL_HOSTNAME', default='')
if RENDER_EXTERNAL_HOSTNAME:
    ALLOWED_HOSTS.append(RENDER_EXTERNAL_HOSTNAME)
    CSRF_TRUSTED_ORIGINS.append(f'https://{RENDER_EXTERNAL_HOSTNAME}')

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'corsheaders',
    'graphene_django',
    'rest_framework_simplejwt.token_blacklist',
    'apps.accounts',
    'apps.destinations',
    'apps.bookings',
    'apps.analytics',
    'apps.core',
    'apps.guides',
    'apps.reviews',
    'apps.payments',
    'apps.notifications',
]

MIDDLEWARE = [
    'config.middleware.HealthCheckMiddleware',
    'django.middleware.security.SecurityMiddleware',
    # Serves the admin's static files from gunicorn, compressed and cached.
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'

# PostgreSQL in staging/production (postgres://user:pass@host:5432/name);
# SQLite for local development.
DATABASES = {
    'default': dj_database_url.parse(
        config('DATABASE_URL', default=f'sqlite:///{BASE_DIR / "db.sqlite3"}'),
        conn_max_age=config('DB_CONN_MAX_AGE', default=60, cast=int),
        conn_health_checks=True,
    )
}

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

STATIC_URL = 'static/'

# Uploaded photos and videos: on disk by default (served by Caddy in the
# deploy/ stack), in an S3-compatible bucket when MEDIA_BUCKET is set.
MEDIA_URL = '/media/'
MEDIA_ROOT = config('MEDIA_ROOT', default=str(BASE_DIR / 'mediafiles'))
MEDIA_MAX_IMAGE_MB = config('MEDIA_MAX_IMAGE_MB', default=15, cast=int)
MEDIA_MAX_VIDEO_MB = config('MEDIA_MAX_VIDEO_MB', default=200, cast=int)
# Uploaded photos are resized to fit this box and stripped of metadata (GPS).
MEDIA_IMAGE_MAX_SIDE = 1920
# Stream uploads to disk instead of memory above 5 MB.
FILE_UPLOAD_MAX_MEMORY_SIZE = 5 * 1024 * 1024
STATIC_ROOT = BASE_DIR / 'staticfiles'
STORAGES = {
    'default': {'BACKEND': 'django.core.files.storage.FileSystemStorage'},
    'staticfiles': {
        'BACKEND': (
            'django.contrib.staticfiles.storage.StaticFilesStorage'
            if DEBUG or TESTING else
            'whitenoise.storage.CompressedManifestStaticFilesStorage'
        ),
    },
}

# S3-compatible object storage (Cloudflare R2, AWS S3, Backblaze B2...) for
# hosts without a persistent disk, such as Render. The bucket must be publicly
# readable at MEDIA_PUBLIC_DOMAIN (R2: r2.dev subdomain or a custom domain).
MEDIA_BUCKET = config('MEDIA_BUCKET', default='')
if MEDIA_BUCKET:
    STORAGES['default'] = {
        'BACKEND': 'storages.backends.s3.S3Storage',
        'OPTIONS': {
            'bucket_name': MEDIA_BUCKET,
            # R2: https://<account id>.r2.cloudflarestorage.com; empty for AWS.
            'endpoint_url': config('MEDIA_ENDPOINT_URL', default='') or None,
            'region_name': config('MEDIA_REGION', default='auto'),
            'access_key': config('MEDIA_ACCESS_KEY_ID', default=''),
            'secret_key': config('MEDIA_SECRET_ACCESS_KEY', default=''),
            # Public, unsigned URLs: the apps cache them.
            'custom_domain': config('MEDIA_PUBLIC_DOMAIN', default='') or None,
            'querystring_auth': False,
            'default_acl': None,
            'file_overwrite': False,
            'object_parameters': {'CacheControl': 'public, max-age=2592000, immutable'},
        },
    }

if TESTING:
    # Password hashing is deliberately slow; tests do not need that.
    PASSWORD_HASHERS = ['django.contrib.auth.hashers.MD5PasswordHasher']
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

AUTH_USER_MODEL = 'accounts.AppUser'

# JWT
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(
        minutes=config('ACCESS_TOKEN_LIFETIME_MINUTES', default=60, cast=int)
    ),
    'REFRESH_TOKEN_LIFETIME': timedelta(
        days=config('REFRESH_TOKEN_LIFETIME_DAYS', default=7, cast=int)
    ),
    'ROTATE_REFRESH_TOKENS': True,
    # A used or signed-out refresh token can never be replayed.
    'BLACKLIST_AFTER_ROTATION': True,
    'ALGORITHM': 'HS256',
    'SIGNING_KEY': config('JWT_SIGNING_KEY', default=SECRET_KEY),
    'AUTH_HEADER_TYPES': ('Bearer',),
}

# GraphQL
GRAPHENE = {
    'SCHEMA': 'config.schema.schema',
    'MIDDLEWARE': [
        'config.middleware.JWTAuthMiddleware',
    ],
}

# CORS
CORS_ALLOWED_ORIGINS = config(
    'CORS_ALLOWED_ORIGINS', default='http://localhost:3000', cast=Csv())
# The API authenticates with bearer tokens only; cookies are never needed.
CORS_ALLOW_CREDENTIALS = False

# ── Bookings ─────────────────────────────────────────────────────────────────
# Flat fee added to every booking total, in euros (shown by the app too).
BOOKING_SERVICE_FEE_EUR = config('BOOKING_SERVICE_FEE_EUR', default=29.0, cast=float)

# Free cancellation until this many days before check-in.
FREE_CANCELLATION_DAYS = config('FREE_CANCELLATION_DAYS', default=7, cast=int)

# ── Operator contact, shown in the app and in emails ─────────────────────────
COMPANY_NAME = config('COMPANY_NAME', default='Akwaba Ivoire')
SUPPORT_EMAIL = config('SUPPORT_EMAIL', default='support@akwaba-ivoire.com')
# International format without '+' or spaces, e.g. 2250700000000.
SUPPORT_WHATSAPP = config('SUPPORT_WHATSAPP', default='')
# Public base URL of this backend, for links in emails and legal pages.
PUBLIC_BASE_URL = config(
    'PUBLIC_BASE_URL', default=config('RENDER_EXTERNAL_URL', default='http://localhost:8000'))

# ── Email ────────────────────────────────────────────────────────────────────
# Development prints emails to the console; production uses SMTP.
EMAIL_BACKEND = config(
    'EMAIL_BACKEND',
    default='django.core.mail.backends.console.EmailBackend' if DEBUG
    else 'django.core.mail.backends.smtp.EmailBackend')
EMAIL_HOST = config('EMAIL_HOST', default='')
EMAIL_PORT = config('EMAIL_PORT', default=587, cast=int)
EMAIL_HOST_USER = config('EMAIL_HOST_USER', default='')
EMAIL_HOST_PASSWORD = config('EMAIL_HOST_PASSWORD', default='')
EMAIL_USE_TLS = config('EMAIL_USE_TLS', default=True, cast=bool)
DEFAULT_FROM_EMAIL = config(
    'DEFAULT_FROM_EMAIL', default=f'{COMPANY_NAME} <{SUPPORT_EMAIL}>')

# ── Payments (Stripe: cards, PayPal, Apple Pay, Google Pay) ──────────────────
STRIPE_SECRET_KEY = config('STRIPE_SECRET_KEY', default='')
STRIPE_PUBLISHABLE_KEY = config('STRIPE_PUBLISHABLE_KEY', default='')
STRIPE_WEBHOOK_SECRET = config('STRIPE_WEBHOOK_SECRET', default='')
PAYMENT_CURRENCY = 'eur'

# ── Push notifications (Firebase Cloud Messaging HTTP v1) ────────────────────
# Path to a Firebase service-account JSON key; push is disabled when empty.
FCM_CREDENTIALS_FILE = config('FCM_CREDENTIALS_FILE', default='')

# ── Error monitoring ─────────────────────────────────────────────────────────
SENTRY_DSN = config('SENTRY_DSN', default='')
if SENTRY_DSN and not TESTING:
    import sentry_sdk

    sentry_sdk.init(
        dsn=SENTRY_DSN,
        environment=APP_ENV,
        traces_sample_rate=config('SENTRY_TRACES_SAMPLE_RATE', default=0.0, cast=float),
        # Never send request bodies, cookies or user details.
        send_default_pii=False,
    )

# ── Social sign-in ───────────────────────────────────────────────────────────
# Firebase project whose ID tokens are accepted by socialSignIn. When empty,
# development (DEBUG) trusts the claims sent by the app; production refuses.
FIREBASE_PROJECT_ID = config('FIREBASE_PROJECT_ID', default='')

# ── Cache (rate limiting) ────────────────────────────────────────────────────
# Use Redis in production so limits are shared by every worker.
REDIS_URL = config('REDIS_URL', default='')
CACHES = {
    'default': (
        {'BACKEND': 'django.core.cache.backends.redis.RedisCache',
         'LOCATION': REDIS_URL}
        if REDIS_URL else
        {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache'}
    )
}

# Number of reverse proxies in front of Django (for the client IP used by
# rate limiting). 0 means REMOTE_ADDR is the client.
NUM_PROXIES = config('NUM_PROXIES', default=0, cast=int)

# ── HTTPS hardening (production) ─────────────────────────────────────────────
if not DEBUG:
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
    SECURE_SSL_REDIRECT = config('SECURE_SSL_REDIRECT', default=True, cast=bool)
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_HSTS_SECONDS = config('SECURE_HSTS_SECONDS', default=31536000, cast=int)
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    SECURE_REFERRER_POLICY = 'same-origin'
    X_FRAME_OPTIONS = 'DENY'

LOG_LEVEL = config('LOG_LEVEL', default='DEBUG' if DEBUG else 'INFO')

# ── Logging ──────────────────────────────────────────────────────────────────
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '[{levelname}] {asctime} {name}: {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
    },
    'loggers': {
        # Every inbound HTTP request + status code
        'django.request': {
            'handlers': ['console'],
            'level': LOG_LEVEL,
            'propagate': False,
        },
        # GraphQL middleware / resolver errors
        'graphene': {
            'handlers': ['console'],
            'level': LOG_LEVEL,
            'propagate': False,
        },
        # Our own apps
        'apps': {
            'handlers': ['console'],
            'level': LOG_LEVEL,
            'propagate': False,
        },
        # GraphQL request body logger (see config/middleware.py)
        'tourism.graphql': {
            'handlers': ['console'],
            'level': LOG_LEVEL,
            'propagate': False,
        },
    },
}
