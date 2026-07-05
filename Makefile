PYTHON = .venv/bin/python
MANAGE = $(PYTHON) manage.py

# setup venv, install deps
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
