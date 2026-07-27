import uuid
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from authsession.models import AuthSession
from authsession.http import ClientContext
from authsession.services import start_auth_session


class LogoutViewTests(TestCase):
    password = "Strong-Test-Password-123!"

    @classmethod
    def setUpTestData(cls):
        cls.user = get_user_model().objects.create_user(
            username="logout-user",
            email="logout@example.com",
            password=cls.password,
        )

    def setUp(self):
        self.client = APIClient(enforce_csrf_checks=True)
        self.csrf_url = reverse("accounts:csrf-token")
        self.login_url = reverse("accounts:login")
        self.logout_url = reverse("accounts:logout")
        self.logout_all_url = reverse("accounts:logout-all")

    def csrf_token(self):
        return self.client.get(self.csrf_url).data["csrf_token"]

    def login(self):
        return self.client.post(
            self.login_url,
            {
                "identifier": self.user.email,
                "password": self.password,
            },
            format="json",
            HTTP_X_CSRFTOKEN=self.csrf_token(),
        )

    def verify_current_session(self):
        AuthSession.objects.filter(
            user=self.user,
            revoked_at__isnull=True,
        ).update(created_at=timezone.now() - timedelta(days=8))
        return self.client.post(
            reverse("accounts:session-verify"),
            {"current_password": self.password},
            format="json",
        )

    def test_logout_revokes_refresh_session_and_clears_login_cookies(self):
        login_response = self.login()
        self.client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {login_response.data['access']}"
        )

        response = self.client.post(
            self.logout_url,
            {},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertIsNotNone(AuthSession.objects.get(user=self.user).revoked_at)
        self.assertEqual(
            response.cookies["refresh_token"]["max-age"],
            0,
        )
        self.assertEqual(
            response.cookies["refresh_token"]["path"],
            "/api/v1/auth/",
        )

    def test_logout_all_revokes_every_device_session(self):
        login_response = self.login()
        start_auth_session(
            user=self.user,
            client_context=ClientContext(
                device_id=uuid.uuid4(),
                device_name="Second device",
                user_agent="Test Browser/2.0",
                ip_address="198.51.100.9",
            ),
        )
        self.client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {login_response.data['access']}"
        )
        self.verify_current_session()

        response = self.client.post(
            self.logout_all_url,
            {},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(
            AuthSession.objects.filter(
                user=self.user,
                revoked_at__isnull=True,
            ).exists()
        )

    def test_logout_all_does_not_revoke_other_users_sessions(self):
        other_user = get_user_model().objects.create_user(
            username="other-logout-user",
            email="other-logout@example.com",
        )
        other_session = start_auth_session(
            user=other_user,
            client_context=ClientContext(
                device_id=uuid.uuid4(),
                device_name="Other device",
                user_agent="Other Browser/1.0",
                ip_address="203.0.113.10",
            ),
        )

        login_response = self.login()
        self.client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {login_response.data['access']}"
        )
        self.verify_current_session()

        response = self.client.post(
            self.logout_all_url,
            {},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertIsNone(
            AuthSession.objects.get(pk=other_session.session_id).revoked_at
        )
