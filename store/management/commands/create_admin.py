from django.core.management.base import BaseCommand
from django.contrib.auth.models import User, Group, Permission
from django.contrib.auth.hashers import make_password
from django.contrib.auth.models import ContentType
from django.apps import apps

class Command(BaseCommand):
    help = 'Creates a default admin user'

    def add_arguments(self, parser):
        parser.add_argument(
            '--username',
            default='admin',
            help='Username for the admin account',
        )
        parser.add_argument(
            '--password',
            default='admin123',
            help='Password for the admin account',
        )
        parser.add_argument(
            '--email',
            default='admin@example.com',
            help='Email for the admin account',
        )

    def handle(self, *args, **options):
        username = options['username']
        password = options['password']
        email = options['email']

        # Check if the user already exists
        if User.objects.filter(username=username).exists():
            self.stdout.write(self.style.WARNING(f'Admin user "{username}" already exists'))
            return

        # Create the admin user
        admin_user = User.objects.create_superuser(
            username=username,
            email=email,
            password=password
        )

        self.stdout.write(self.style.SUCCESS(f'Admin user "{username}" created successfully with password "{password}"'))
        self.stdout.write(self.style.SUCCESS(f'You can now log in at /login/ with these credentials')) 