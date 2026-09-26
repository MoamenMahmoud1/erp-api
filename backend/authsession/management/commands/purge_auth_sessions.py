from django.core.management.base import BaseCommand, CommandError

from authsession.services.cleanup import purge_auth_sessions


class Command(BaseCommand):
    help = "Delete expired sessions and revoked sessions past the retention period."

    def add_arguments(self, parser):
        parser.add_argument("--revoked-retention-days", type=int, default=30)

    def handle(self, *args, **options):
        retention_days = options["revoked_retention_days"]
        if retention_days < 0:
            raise CommandError("Retention days cannot be negative.")

        deleted_count = purge_auth_sessions(
            revoked_retention_days=retention_days,
        )
        self.stdout.write(self.style.SUCCESS(f"Deleted {deleted_count} session rows."))
