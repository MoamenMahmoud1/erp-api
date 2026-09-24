import uuid
from urllib.parse import parse_qs, urlparse

from django.contrib.auth import get_user_model
from django.core import mail
from django.core.cache import cache
from django.test import TestCase, override_settings
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from authsession.http import ClientContext
from authsession.models import AuthSession
from authsession.services import start_auth_session


@override_settings(
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
    FRONTEND_URL="https://app.example.com",
)
class PasswordResetTests(TestCase):
    password = "Strong-Test-Password-123!"
    new_password = "Another-Strong-Password-456!"

    @classmethod
    def setUpTestData(cls):
        cls.user = get_user_model().objects.create_user(
            username="password-reset-user",
            email="password-reset@example.com",
            password=cls.password,
        )

    def setUp(self):
        cache.clear()
        self.client = APIClient(enforce_csrf_checks=True)
        self.request_url = reverse("accounts:password-reset")
        self.confirm_url = reverse("accounts:password-reset-confirm")

    def request_reset(self, email=None):
        return self.client.post(
            self.request_url,
            {"email": email or self.user.email},
            format="json",
        )

    def reset_credentials_from_email(self):
        reset_url = next(
            line
            for line in mail.outbox[-1].body.splitlines()
            if line.startswith("https://")
        )
        query = parse_qs(urlparse(reset_url).query)
        return query["uid"][0], query["token"][0]

    def test_request_sends_reset_link_without_revealing_account_data(self):
        response = self.request_reset(email="PASSWORD-RESET@example.com")

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, [self.user.email])

    def test_unknown_email_returns_same_response_without_sending_email(self):
        response = self.request_reset(email="missing@example.com")

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(len(mail.outbox), 0)

    def test_confirm_changes_password_revokes_sessions_and_clears_cookies(self):
        session = start_auth_session(
            user=self.user,
            client_context=ClientContext(
                device_id=uuid.uuid4(),
                device_name="Reset device",
                user_agent="Test Browser/1.0",
                ip_address="192.0.2.20",
            ),
        )
        self.request_reset()
        uid, token = self.reset_credentials_from_email()

        response = self.client.post(
            self.confirm_url,
            {
                "uid": uid,
                "token": token,
                "new_password": self.new_password,
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password(self.new_password))
        self.assertIsNotNone(
            AuthSession.objects.get(pk=session.session_id).revoked_at
        )
        self.assertEqual(response.cookies["refresh_token"]["max-age"], 0)

    def test_confirm_rejects_token_reuse(self):
        self.request_reset()
        uid, token = self.reset_credentials_from_email()
        payload = {
            "uid": uid,
            "token": token,
            "new_password": self.new_password,
        }

        first_response = self.client.post(self.confirm_url, payload, format="json")
        second_response = self.client.post(self.confirm_url, payload, format="json")

        self.assertEqual(first_response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(second_response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_confirm_runs_django_password_validation(self):
        self.request_reset()
        uid, token = self.reset_credentials_from_email()

        response = self.client.post(
            self.confirm_url,
            {"uid": uid, "token": token, "new_password": "password"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("new_password", response.data)
