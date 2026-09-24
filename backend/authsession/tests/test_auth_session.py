import uuid
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.test import TestCase
from django.utils import timezone

from authsession.models import AuthSession


class AuthSessionTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = get_user_model().objects.create_user(
            username="ahmed",
            email="ahmed@example.com",
        )

    def create_session(self, **overrides):
        values = {
            "user": self.user,
            "current_refresh_jti": uuid.uuid4(),
            "expires_at": timezone.now() + timedelta(hours=8),
            "device_name": "Ahmed's browser",
            "user_agent": "Test browser",
            "ip_address": "127.0.0.1",
        }
        values.update(overrides)
        return AuthSession.objects.create(**values)

    def test_new_unexpired_session_is_active(self):
        auth_session = self.create_session()

        self.assertTrue(auth_session.is_active)
        self.assertIsNone(auth_session.revoked_at)

    def test_revoked_session_is_inactive(self):
        auth_session = self.create_session(revoked_at=timezone.now())

        self.assertFalse(auth_session.is_active)

    def test_expired_session_is_inactive(self):
        auth_session = self.create_session(
            expires_at=timezone.now() - timedelta(seconds=1),
        )

        self.assertFalse(auth_session.is_active)

    def test_refresh_jti_identifies_only_one_session(self):
        refresh_jti = uuid.uuid4()
        self.create_session(current_refresh_jti=refresh_jti)

        with self.assertRaises(IntegrityError), transaction.atomic():
            self.create_session(current_refresh_jti=refresh_jti)

    def test_device_id_is_generated_independently_from_session_id(self):
        auth_session = self.create_session()

        self.assertIsInstance(auth_session.device_id, uuid.UUID)
        self.assertNotEqual(auth_session.device_id, auth_session.id)

    def test_only_one_active_session_is_allowed_per_user_device(self):
        device_id = uuid.uuid4()
        self.create_session(device_id=device_id)

        with self.assertRaises(IntegrityError), transaction.atomic():
            self.create_session(device_id=device_id)
