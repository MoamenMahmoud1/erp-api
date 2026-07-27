import uuid

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework_simplejwt.tokens import AccessToken, RefreshToken

from authsession.http import ClientContext
from authsession.models import AuthSession
from authsession.services.auth_session import (
    InvalidAuthSession,
    refresh_auth_session,
    start_auth_session,
)


class RefreshAuthSessionServiceTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = get_user_model().objects.create_user(
            username="ahmed",
            email="ahmed@example.com",
        )

    def setUp(self):
        self.context = ClientContext(
            device_id=uuid.uuid4(),
            device_name="Ahmed Laptop",
            user_agent="Test Browser/1.0",
            ip_address="192.0.2.10",
        )
        self.login_result = start_auth_session(
            user=self.user,
            client_context=self.context,
        )

    def test_rotates_refresh_and_updates_same_database_session(self):
        old_refresh = RefreshToken(self.login_result.refresh_token)

        result = refresh_auth_session(
            refresh_token=self.login_result.refresh_token,
            client_context=self.context,
        )

        auth_session = AuthSession.objects.get(id=self.login_result.session_id)
        new_refresh = RefreshToken(result.refresh_token)
        new_access = AccessToken(result.access_token)

        self.assertNotEqual(new_refresh["jti"], old_refresh["jti"])
        self.assertEqual(uuid.UUID(new_refresh["sid"]), auth_session.id)
        self.assertEqual(uuid.UUID(new_access["sid"]), auth_session.id)
        self.assertEqual(
            uuid.UUID(new_refresh["jti"]),
            auth_session.current_refresh_jti,
        )
        self.assertEqual(AuthSession.objects.count(), 1)
        self.assertGreater(result.refresh_max_age, 0)

    def test_reusing_rotated_refresh_revokes_whole_session(self):
        old_refresh = self.login_result.refresh_token
        refresh_auth_session(
            refresh_token=old_refresh,
            client_context=self.context,
        )

        with self.assertRaises(InvalidAuthSession):
            refresh_auth_session(
                refresh_token=old_refresh,
                client_context=self.context,
            )

        auth_session = AuthSession.objects.get(id=self.login_result.session_id)
        self.assertIsNotNone(auth_session.revoked_at)

    def test_refresh_from_different_device_revokes_session(self):
        other_device = ClientContext(
            device_id=uuid.uuid4(),
            device_name="Unknown device",
            user_agent="Other Browser",
            ip_address="198.51.100.20",
        )

        with self.assertRaises(InvalidAuthSession):
            refresh_auth_session(
                refresh_token=self.login_result.refresh_token,
                client_context=other_device,
            )

        auth_session = AuthSession.objects.get(id=self.login_result.session_id)
        self.assertIsNotNone(auth_session.revoked_at)
