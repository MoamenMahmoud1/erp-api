from datetime import timedelta

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from payments.models import IdempotencyKey


class Command(BaseCommand):
    help = "Delete expired persisted idempotency keys after the configured retention window."

    def add_arguments(self, parser):
        parser.add_argument(
            "--days",
            type=int,
            default=None,
            help="Override IDEMPOTENCY_RETENTION_DAYS for this run.",
        )

    def handle(self, *args, **options):
        days = options["days"]
        if days is None:
            days = settings.IDEMPOTENCY_RETENTION_DAYS
        if days < 1:
            raise CommandError("Retention days must be >= 1.")

        cutoff = timezone.now() - timedelta(days=days)
        deleted, _ = IdempotencyKey.objects.filter(created_at__lt=cutoff).delete()

        self.stdout.write(
            self.style.SUCCESS(
                f"Deleted {deleted} expired idempotency records (older than {days} days)."
            )
        )
