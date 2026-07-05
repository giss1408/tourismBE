from django.core.management.base import BaseCommand
from django.conf import settings
from apps.accounts.models import AppUser


class Command(BaseCommand):
    help = 'Create a default superuser for development if one does not exist.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--email',
            default='admin@tourismapp.dev',
            help='Admin email (default: admin@tourismapp.dev)',
        )
        parser.add_argument(
            '--password',
            default='Admin1234!',
            help='Admin password (default: Admin1234!)',
        )
        parser.add_argument(
            '--display-name',
            default='Admin',
            help='Admin display name (default: Admin)',
        )

    def handle(self, *args, **options):
        email = options['email']
        password = options['password']
        display_name = options['display_name']

        if AppUser.objects.filter(email=email).exists():
            self.stdout.write(self.style.WARNING(f'Admin user already exists: {email}'))
            return

        AppUser.objects.create_superuser(
            email=email,
            password=password,
            display_name=display_name,
        )
        self.stdout.write(self.style.SUCCESS(f'Superuser created: {email}'))

        if settings.DEBUG:
            self.stdout.write(
                self.style.NOTICE(
                    f'  Password: {password} — change this before deploying to production.'
                )
            )
