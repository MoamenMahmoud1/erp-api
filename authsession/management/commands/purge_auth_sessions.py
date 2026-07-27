from datetime import timedelta

from django.core.management.base import BaseCommand, CommandError
from django.db.models import Q
from django.utils import timezone

from authsession.models import AuthSession


class Command(BaseCommand):
    help = "Delete expired sessions and revoked sessions past the retention period."

    def add_arguments(self, parser):
        parser.add_argument("--revoked-retention-days", type=int, default=30)

    def handle(self, *args, **options):
        retention_days = options["revoked_retention_days"]
        if retention_days < 0:
            raise CommandError("Retention days cannot be negative.")

        now = timezone.now()
        revoked_cutoff = now - timedelta(days=retention_days)
        deleted_count, _ = AuthSession.objects.filter(
            Q(expires_at__lte=now)
            | Q(revoked_at__isnull=False, revoked_at__lte=revoked_cutoff)
        ).delete()
        self.stdout.write(self.style.SUCCESS(f"Deleted {deleted_count} session rows."))
