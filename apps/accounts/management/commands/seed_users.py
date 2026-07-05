from django.core.management.base import BaseCommand
from apps.accounts.models import AppUser

SEED_USERS = [
    {
        'email': 'test@example.com',
        'password': 'Test1234!',
        'display_name': 'Test Traveler',
    },
    {
        'email': 'demo@tourismapp.dev',
        'password': 'Demo1234!',
        'display_name': 'Demo User',
    },
]


class Command(BaseCommand):
    help = 'Seed test user accounts for local development.'

    def handle(self, *args, **options):
        created = 0
        skipped = 0

        for data in SEED_USERS:
            if AppUser.objects.filter(email=data['email']).exists():
                skipped += 1
                continue
            AppUser.objects.create_user(
                email=data['email'],
                password=data['password'],
                display_name=data['display_name'],
            )
            created += 1

        self.stdout.write(
            self.style.SUCCESS(f'Test users: {created} created, {skipped} already existed.')
        )
        self.stdout.write('')
        self.stdout.write('Available accounts:')
        self.stdout.write('  admin@tourismapp.dev  /  Admin1234!  (superuser)')
        for u in SEED_USERS:
            self.stdout.write(f'  {u["email"]}  /  {u["password"]}')
