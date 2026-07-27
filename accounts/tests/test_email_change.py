from datetime import timedelta
from urllib.parse import parse_qs, urlparse

from django.contrib.auth import authenticate, get_user_model
from django.core import mail
from django.core.cache import cache
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from authsession.models import AuthSession


@override_settings(
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
    FRONTEND_URL="https://app.example.com",
)
class EmailChangeTests(TestCase):
    password = "Strong-Email-Password-123!"

    @classmethod
    def setUpTestData(cls):
        cls.user = get_user_model().objects.create_user(
            username="email-change-user",
            email="old-email@example.com",
            password=cls.password,
            is_verified=True,
        )

    def setUp(self):
        cache.clear()
        self.client = APIClient(enforce_csrf_checks=True)
        self.change_url = reverse("accounts:email-change")
        self.confirm_url = reverse("accounts:email-change-confirm")
        csrf_response = self.client.get(reverse("accounts:csrf-token"))
        login_response = self.client.post(
            reverse("accounts:login"),
            {"identifier": self.user.email, "password": self.password},
            format="json",
            HTTP_X_CSRFTOKEN=csrf_response.data["csrf_token"],
        )
        self.client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {login_response.data['access']}"
        )

    def verify_current_session(self, password=None):
        AuthSession.objects.filter(
            user=self.user,
            revoked_at__isnull=True,
        ).update(created_at=timezone.now() - timedelta(days=8))
        return self.client.post(
            reverse("accounts:session-verify"),
            {"current_password": password or self.password},
            format="json",
        )

    def request_change(self, new_email="new-email@example.com"):
        return self.client.post(
            self.change_url,
            {"new_email": new_email},
            format="json",
        )

    def token_from_latest_email(self):
        verification_url = next(
            line
            for line in mail.outbox[-1].body.splitlines()
            if line.startswith("https://")
        )
        return parse_qs(urlparse(verification_url).query)["token"][0]

    def test_change_request_requires_trusted_session(self):
        unverified_response = self.request_change()
        verification_response = self.verify_current_session()
        change_response = self.request_change()

        self.assertEqual(unverified_response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(verification_response.status_code, status.HTTP_200_OK)
        self.assertEqual(change_response.status_code, status.HTTP_204_NO_CONTENT)
        self.user.refresh_from_db()
        self.assertEqual(self.user.email, "old-email@example.com")
        self.assertEqual(mail.outbox[-1].to, ["new-email@example.com"])

    def test_session_younger_than_one_week_cannot_be_trusted(self):
        AuthSession.objects.filter(
            user=self.user,
            revoked_at__isnull=True,
        ).update(created_at=timezone.now() - timedelta(days=6))

        response = self.client.post(
            reverse("accounts:session-verify"),
            {"current_password": self.password},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(response.data["code"], "session_too_new")

    def test_confirmation_changes_email_immediately_and_revokes_sessions(self):
        self.verify_current_session()
        self.request_change()
        token = self.token_from_latest_email()

        response = self.client.post(
            self.confirm_url,
            {"token": token},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.user.refresh_from_db()
        self.assertEqual(self.user.email, "new-email@example.com")
        self.assertFalse(
            AuthSession.objects.filter(
                user=self.user,
                revoked_at__isnull=True,
            ).exists()
        )
        self.assertEqual(mail.outbox[-1].to, ["old-email@example.com"])
        self.assertEqual(response.cookies["refresh_token"]["max-age"], 0)
        self.assertEqual(
            authenticate(username=self.user.email, password=self.password),
            self.user,
        )

    def test_confirmation_link_is_single_use(self):
        self.verify_current_session()
        self.request_change()
        token = self.token_from_latest_email()

        first_response = self.client.post(
            self.confirm_url,
            {"token": token},
            format="json",
        )
        second_response = self.client.post(
            self.confirm_url,
            {"token": token},
            format="json",
        )

        self.assertEqual(first_response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(second_response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_existing_email_is_rejected_case_insensitively(self):
        get_user_model().objects.create_user(
            username="email-owner",
            email="owned@example.com",
        )
        self.verify_current_session()

        response = self.request_change(new_email="OWNED@example.com")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("new_email", response.data)
