# Akwaba Ivoire – backend

Django 5.2 + GraphQL (graphene) API for the Akwaba Ivoire travel app:
destinations, bookings, Stripe payments, reviews, local guides, push
notifications and transactional emails.

## Local development

Requires Python 3.12+.

```sh
cp .env.example .env
make setup migrate seed   # seed = test destinations and accounts
make run                  # http://localhost:8000/graphql/ (GraphiQL in DEBUG)
make test
```

Test accounts after `make seed`: `test@example.com` / `Test1234!`,
`demo@tourismapp.dev` / `Demo1234!`, `admin@tourismapp.dev` / `Admin1234!`
(admin at `/admin/`).

To run against PostgreSQL like production: `docker compose up`.

Android phone over USB: `adb reverse tcp:8000 tcp:8000`, then run the app
with `GRAPHQL_ENDPOINT=http://localhost:8000/graphql/`.

## Configuration

Everything is configured with environment variables:

| File | Environment |
| --- | --- |
| `.env.example` | local development |
| `deploy/env.staging.example` | staging (Stripe test keys) |
| `deploy/env.production.example` | production |

Production refuses to start without `SECRET_KEY`, and is the default: `DEBUG`
must be set to `True` explicitly for development.

## Deployment

The production stack (`deploy/docker-compose.prod.yml`) runs:

- **caddy**: HTTPS with automatic Let's Encrypt certificates for `API_DOMAIN`;
- **web**: gunicorn, migrations on start, health check on `/healthz/`;
- **db**: PostgreSQL 16; **redis**: shared cache for rate limiting;
- **scheduler**: cron for trip reminders (09:00 UTC) and database backups
  (02:30 UTC, into `deploy/backups/`, kept `BACKUP_RETENTION_DAYS` days).

```sh
cp deploy/env.production.example deploy/production.env   # fill every CHANGE_ME
mkdir -p deploy/secrets   # firebase-service-account.json for push
make deploy               # docker compose up -d --build
docker compose -f deploy/docker-compose.prod.yml exec web python manage.py createsuperuser
```

Point the DNS record of `API_DOMAIN` to the server before starting (Caddy needs
it for the certificate). Copy `deploy/backups/` off the server regularly.

### Stripe

1. Enable card, PayPal, Apple Pay and Google Pay in the Stripe dashboard
   (Settings › Payment methods): the app offers whatever is enabled.
2. Add a webhook endpoint `https://API_DOMAIN/payments/stripe/webhook/` for
   `payment_intent.succeeded` and `payment_intent.payment_failed`, and put its
   signing secret in `STRIPE_WEBHOOK_SECRET`.

A successful payment confirms the booking and emails the traveller.
Cancellations up to `FREE_CANCELLATION_DAYS` before check-in are refunded
automatically.

### Firebase

- `FIREBASE_PROJECT_ID`: social sign-in tokens are verified against it.
- `FCM_CREDENTIALS_FILE`: service-account key (Firebase console › Project
  settings › Service accounts) to send push notifications.

## Operations

- Confirm or cancel bookings in the admin (Bookings › actions): travellers get
  an email and a push notification.
- Legal pages: `/legal/privacy/?lang=fr|en|de` and `/legal/terms/?lang=…`
  (drafts to be reviewed by a lawyer).
- Errors are reported to Sentry when `SENTRY_DSN` is set.
