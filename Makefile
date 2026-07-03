# setup venv, install deps and run migrations
setup:
	python -m venv .venv && . .venv/bin/activate && pip install -r requirements.txt

migrate:
	python manage.py migrate

makemigrations:
	python manage.py makemigrations

createsuperuser:
	python manage.py createsuperuser

run:
	python manage.py runserver

test:
	python manage.py test apps --verbosity=2

shell:
	python manage.py shell
