from datetime import timedelta

from django.core.management import call_command
from django.test import TestCase, override_settings
from django.utils import timezone

from accounts.models import CustomUserModel
from payments.models import IdempotencyKey


class IdempotencyCleanupTests(TestCase):
    def setUp(self):
        self.user = CustomUserModel.objects.create_user(
            username="cleanup-user",
            email="cleanup@example.com",
            password="StrongPass123!",
        )

    @override_settings(IDEMPOTENCY_RETENTION_DAYS=90)
    def test_purges_records_older_than_configured_retention(self):
        old = IdempotencyKey.objects.create(
            key="old-key",
            user=self.user,
            path="/api/v1/payments/collections/",
            request_signature="a" * 64,
            response_status=201,
            response_body={"id": 1},
        )
        IdempotencyKey.objects.filter(pk=old.pk).update(
            created_at=timezone.now() - timedelta(days=91),
        )
        fresh = IdempotencyKey.objects.create(
            key="fresh-key",
            user=self.user,
            path="/api/v1/payments/collections/",
            request_signature="b" * 64,
            response_status=201,
            response_body={"id": 2},
        )

        call_command("purge_idempotency_keys")

        self.assertFalse(IdempotencyKey.objects.filter(pk=old.pk).exists())
        self.assertTrue(IdempotencyKey.objects.filter(pk=fresh.pk).exists())
