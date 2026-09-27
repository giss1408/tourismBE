PYTHON = .venv/bin/python
MANAGE = $(PYTHON) manage.py
PROD_COMPOSE = docker compose -f deploy/docker-compose.prod.yml

# setup venv, install deps (Python 3.12+)
setup:
	python3 -m venv .venv && .venv/bin/pip install -r requirements.txt

migrate:
	$(MANAGE) migrate

makemigrations:
	$(MANAGE) makemigrations

createsuperuser:
	$(MANAGE) createsuperuser

create_admin:
	$(MANAGE) create_admin

run:
	$(MANAGE) runserver 0.0.0.0:8000

test:
	$(MANAGE) test apps --verbosity=2

seed:
	$(MANAGE) seed_destinations
	$(MANAGE) seed_users

shell:
	$(MANAGE) shell

check-deploy:
	DEBUG=False $(MANAGE) check --deploy

reminders:
	$(MANAGE) send_trip_reminders

# Production stack (see README "Deployment")
deploy:
	$(PROD_COMPOSE) up -d --build

deploy-logs:
	$(PROD_COMPOSE) logs -f --tail=100

backup:
	./scripts/backup_db.sh ./backups
