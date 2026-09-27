# Production image: gunicorn behind a TLS-terminating proxy (Render, or
# deploy/docker-compose.prod.yml). Development can keep using `make run`.
FROM python:3.12-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# postgresql-client: pg_dump for scripts/backup_db.sh; cron: the scheduler
# service (scripts/scheduler.sh).
RUN apt-get update \
    && apt-get install -y --no-install-recommends postgresql-client cron \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

# collectstatic needs settings but no secrets or database.
RUN DEBUG=True SECRET_KEY=build-only python manage.py collectstatic --noinput

RUN useradd --create-home --uid 1000 app && chown -R app /app
USER app

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD python -c "import os, urllib.request; urllib.request.urlopen('http://127.0.0.1:%s/healthz/' % os.environ.get('PORT', '8000'))" || exit 1

# PORT is set by hosts such as Render. RUN_MIGRATIONS=0 when the host runs
# them as a separate pre-deploy step (see render.yaml).
CMD ["sh", "-c", "if [ \"${RUN_MIGRATIONS:-1}\" = 1 ]; then python manage.py migrate --noinput; fi && exec gunicorn config.wsgi:application --bind 0.0.0.0:${PORT:-8000} --workers ${GUNICORN_WORKERS:-3} --timeout 300 --access-logfile -"]
