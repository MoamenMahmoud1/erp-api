import uuid

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import AccessToken, RefreshToken

from authsession.models import AuthSession


class LoginViewTests(TestCase):
    password = "Strong-Test-Password-123!"

    @classmethod
    def setUpTestData(cls):
        cls.user = get_user_model().objects.create_user(
            username="ahmed",
            email="ahmed@example.com",
            password=cls.password,
        )

    def setUp(self):
        cache.clear()
        self.client = APIClient(enforce_csrf_checks=True)
        self.csrf_url = reverse("accounts:csrf-token")
        self.login_url = reverse("accounts:login")

    def login_data(self):
        return {
            "identifier": self.user.email,
            "password": self.password,
        }

    def login_with_csrf(self, **request_headers):
        csrf_response = self.client.get(self.csrf_url)
        return self.client.post(
            self.login_url,
            self.login_data(),
            format="json",
            HTTP_X_CSRFTOKEN=csrf_response.data["csrf_token"],
            **request_headers,
        )

    def test_csrf_endpoint_returns_token_and_sets_cookie(self):
        response = self.client.get(self.csrf_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("csrf_token", response.data)
        self.assertIn("csrftoken", response.cookies)

    def test_login_rejects_request_without_csrf_token(self):
        response = self.client.post(
            self.login_url,
            self.login_data(),
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_login_accepts_valid_csrf_and_stores_refresh_in_httponly_cookie(self):
        csrf_response = self.client.get(self.csrf_url)
        csrf_token = csrf_response.data["csrf_token"]

        response = self.client.post(
            self.login_url,
            self.login_data(),
            format="json",
            HTTP_X_CSRFTOKEN=csrf_token,
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access", response.data)
        self.assertNotIn("refresh", response.data)
        self.assertIn("refresh_token", response.cookies)
        self.assertTrue(response.cookies["refresh_token"]["httponly"])
        self.assertEqual(response.cookies["refresh_token"]["samesite"], "Lax")
        self.assertEqual(response.cookies["refresh_token"]["path"], "/api/v1/auth/")

    def test_login_rejects_untrusted_origin_even_with_valid_csrf_token(self):
        csrf_response = self.client.get(self.csrf_url)

        response = self.client.post(
            self.login_url,
            self.login_data(),
            format="json",
            HTTP_X_CSRFTOKEN=csrf_response.data["csrf_token"],
            HTTP_ORIGIN="https://attacker.example",
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_failed_login_response_is_not_cacheable(self):
        csrf_response = self.client.get(self.csrf_url)
        payload = self.login_data()
        payload["password"] = "Wrong-Password-123!"

        response = self.client.post(
            self.login_url,
            payload,
            format="json",
            HTTP_X_CSRFTOKEN=csrf_response.data["csrf_token"],
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertIn("no-store", response["Cache-Control"])
        self.assertIn("private", response["Cache-Control"])
        self.assertEqual(response["Pragma"], "no-cache")

    def test_login_creates_session_bound_to_both_tokens(self):
        response = self.login_with_csrf(
            HTTP_USER_AGENT="Test Browser/1.0",
            REMOTE_ADDR="192.0.2.10",
        )

        auth_session = AuthSession.objects.get(user=self.user)
        refresh = RefreshToken(response.cookies["refresh_token"].value)
        access = AccessToken(response.data["access"])

        self.assertEqual(uuid.UUID(refresh["sid"]), auth_session.id)
        self.assertEqual(uuid.UUID(access["sid"]), auth_session.id)
        self.assertEqual(
            uuid.UUID(refresh["jti"]),
            auth_session.current_refresh_jti,
        )
        self.assertEqual(refresh["exp"], int(auth_session.expires_at.timestamp()))
        self.assertEqual(auth_session.user_agent, "Test Browser/1.0")
        self.assertEqual(auth_session.ip_address, "192.0.2.10")

    def test_first_login_sets_protected_device_cookie(self):
        response = self.login_with_csrf()

        self.assertIn("device_id", response.cookies)
        device_cookie = response.cookies["device_id"]
        self.assertTrue(device_cookie["httponly"])
        self.assertEqual(device_cookie["samesite"], "Lax")
        self.assertEqual(device_cookie["path"], "/api/v1/auth/")

    def test_new_login_on_same_device_revokes_previous_session(self):
        first_response = self.login_with_csrf()
        first_session = AuthSession.objects.get(user=self.user)

        second_response = self.login_with_csrf()
        first_session.refresh_from_db()
        active_session = AuthSession.objects.get(user=self.user, revoked_at__isnull=True)

        self.assertEqual(first_response.status_code, status.HTTP_200_OK)
        self.assertEqual(second_response.status_code, status.HTTP_200_OK)
        self.assertIsNotNone(first_session.revoked_at)
        self.assertEqual(active_session.device_id, first_session.device_id)
