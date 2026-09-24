import uuid
from pathlib import Path

from django.core.management.base import BaseCommand

from accounts.models import CustomUserModel
from authsession.http import ClientContext
from authsession.services.auth_session import start_auth_session


PASSWORD = "Benchmark!2026"
USERNAME_PREFIX = "benchmark_user_"
EMAIL_DOMAIN = "benchmark.local"


class Command(BaseCommand):
    help = "Create benchmark users and active JWT/Redis auth sessions."

    def add_arguments(self, parser):
        parser.add_argument(
            "--count",
            type=int,
            default=100,
            help="Number of benchmark users to create/update.",
        )

    def handle(self, *args, **options):
        count = options["count"]
        if count < 1:
            self.stderr.write(self.style.ERROR("--count must be >= 1"))
            return

        for index in range(1, count + 1):
            username = f"{USERNAME_PREFIX}{index:04d}"
            email = f"{username}@{EMAIL_DOMAIN}"

            user, created = CustomUserModel.objects.get_or_create(
                username=username,
                defaults={
                    "email": email,
                    "is_active": True,
                    "is_verified": True,
                    "first_name": "Benchmark",
                    "last_name": f"User {index:04d}",
                },
            )

            changed = False

            if user.email.lower() != email.lower():
                user.email = email
                changed = True
            if not user.is_active:
                user.is_active = True
                changed = True
            if not user.is_verified:
                user.is_verified = True
                changed = True

            user.set_password(PASSWORD)
            changed = True

            if changed:
                user.save()

            device_id = uuid.uuid5(
                uuid.NAMESPACE_URL,
                f"erp-api-benchmark-device:{username}",
            )

            session = start_auth_session(
                user=user,
                client_context=ClientContext(
                    device_id=device_id,
                    device_name="benchmark",
                    user_agent="erp-api-benchmark/1.0",
                    ip_address="127.0.0.1",
                ),
            )

            self.stdout.write(session.access_token)

        self.stderr.write(
            self.style.SUCCESS(
                f"Prepared {count} benchmark users. "
                f"Password for all users: {PASSWORD}"
            )
        )
