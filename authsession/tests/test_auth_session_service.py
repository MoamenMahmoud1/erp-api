import uuid

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework_simplejwt.tokens import AccessToken, RefreshToken

from authsession.http import ClientContext
from authsession.models import AuthSession
from authsession.services.auth_session import start_auth_session


class AuthSessionServiceTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = get_user_model().objects.create_user(
            username="ahmed",
            email="ahmed@example.com",
        )

    def make_context(self, *, device_id=None):
        return ClientContext(
            device_id=device_id or uuid.uuid4(),
            device_name="Ahmed Laptop",
            user_agent="Test Browser/1.0",
            ip_address="192.0.2.10",
        )

    def start_session(self, *, context=None):
        return start_auth_session(
            user=self.user,
            client_context=context or self.make_context(),
        )

    def test_creates_database_session_bound_to_returned_tokens(self):
        result = self.start_session()

        auth_session = AuthSession.objects.get(user=self.user)
        refresh = RefreshToken(result.refresh_token)
        access = AccessToken(result.access_token)

        self.assertEqual(uuid.UUID(refresh["sid"]), auth_session.id)
        self.assertEqual(uuid.UUID(access["sid"]), auth_session.id)
        self.assertEqual(
            uuid.UUID(refresh["jti"]),
            auth_session.current_refresh_jti,
        )
        self.assertEqual(result.device_id, auth_session.device_id)
        self.assertEqual(auth_session.device_name, "Ahmed Laptop")
        self.assertEqual(auth_session.user_agent, "Test Browser/1.0")
        self.assertEqual(auth_session.ip_address, "192.0.2.10")

    def test_new_session_on_same_device_revokes_previous_session(self):
        context = self.make_context()
        first_result = self.start_session(context=context)
        first_session = AuthSession.objects.get(id=first_result.session_id)

        second_result = self.start_session(context=context)
        first_session.refresh_from_db()

        self.assertIsNotNone(first_session.revoked_at)
        self.assertNotEqual(first_result.session_id, second_result.session_id)
        self.assertEqual(
            AuthSession.objects.filter(
                user=self.user,
                device_id=context.device_id,
                revoked_at__isnull=True,
            ).count(),
            1,
        )

    def test_different_devices_keep_independent_active_sessions(self):
        self.start_session(context=self.make_context())
        self.start_session(context=self.make_context())

        self.assertEqual(
            AuthSession.objects.filter(
                user=self.user,
                revoked_at__isnull=True,
            ).count(),
            2,
        )
