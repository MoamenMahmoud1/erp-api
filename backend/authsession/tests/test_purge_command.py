import uuid
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase
from django.utils import timezone

from authsession.models import AuthSession


class PurgeAuthSessionsCommandTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = get_user_model().objects.create_user(
            username="purge-user",
            email="purge-user@example.com",
        )

    def create_session(self, **overrides):
        values = {
            "user": self.user,
            "device_id": uuid.uuid4(),
            "current_refresh_jti": uuid.uuid4(),
            "expires_at": timezone.now() + timedelta(hours=1),
        }
        values.update(overrides)
        return AuthSession.objects.create(**values)

    def test_deletes_expired_and_old_revoked_sessions_only(self):
        expired = self.create_session(
            expires_at=timezone.now() - timedelta(seconds=1),
        )
        old_revoked = self.create_session(
            revoked_at=timezone.now() - timedelta(days=31),
        )
        recent_revoked = self.create_session(revoked_at=timezone.now())
        active = self.create_session()

        call_command("purge_auth_sessions", verbosity=0)

        remaining_ids = set(AuthSession.objects.values_list("id", flat=True))
        self.assertNotIn(expired.id, remaining_ids)
        self.assertNotIn(old_revoked.id, remaining_ids)
        self.assertIn(recent_revoked.id, remaining_ids)
        self.assertIn(active.id, remaining_ids)
