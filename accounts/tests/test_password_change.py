from datetime import timedelta

from django.contrib.auth import authenticate, get_user_model
from django.core.cache import cache
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from authsession.models import AuthSession


class PasswordChangeTests(TestCase):
    password = "Strong-Current-Password-123!"
    new_password = "Strong-New-Password-456!"

    @classmethod
    def setUpTestData(cls):
        cls.user = get_user_model().objects.create_user(
            username="password-change-user",
            email="password-change@example.com",
            password=cls.password,
        )

    def setUp(self):
        cache.clear()
        self.client = APIClient(enforce_csrf_checks=True)
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
        self.session = AuthSession.objects.get(
            user=self.user,
            revoked_at__isnull=True,
        )

    def verify_current_session(self):
        AuthSession.objects.filter(pk=self.session.pk).update(
            created_at=timezone.now() - timedelta(days=8)
        )
        return self.client.post(
            reverse("accounts:session-verify"),
            {"current_password": self.password},
            format="json",
        )

    def change_password(self, **overrides):
        payload = {
            "new_password": self.new_password,
            "password_confirm": self.new_password,
        }
        payload.update(overrides)
        return self.client.post(
            reverse("accounts:password-change"),
            payload,
            format="json",
        )

    def test_verified_session_can_change_password_and_sessions_are_revoked(self):
        verification_response = self.verify_current_session()

        response = self.change_password()

        self.assertEqual(verification_response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.session.refresh_from_db()
        self.assertIsNotNone(self.session.revoked_at)
        self.assertIsNone(
            authenticate(username=self.user.email, password=self.password)
        )
        self.assertEqual(
            authenticate(username=self.user.email, password=self.new_password),
            self.user,
        )

    def test_password_change_requires_recent_session_verification(self):
        response = self.change_password()

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_expired_session_verification_is_rejected(self):
        self.verify_current_session()
        AuthSession.objects.filter(pk=self.session.pk).update(
            verified_at=timezone.now() - timedelta(minutes=16)
        )

        response = self.change_password()

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_password_confirmation_must_match(self):
        self.verify_current_session()

        response = self.change_password(password_confirm="Different-Password-789!")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("password_confirm", response.data)
