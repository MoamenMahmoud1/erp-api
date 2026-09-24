from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import TestCase
from django.urls import reverse
from rest_framework import status

from authsession.models import AuthSession
from core.testing.auth import login_client, new_api_client


class RefreshViewTests(TestCase):
    password = "Strong-Test-Password-123!"

    @classmethod
    def setUpTestData(cls):
        cls.user = get_user_model().objects.create_user(
            username="ahmed-refresh",
            email="ahmed-refresh@example.com",
            password=cls.password,
        )

    def setUp(self):
        cache.clear()
        self.client = new_api_client()
        self.refresh_url = reverse("accounts:refresh")

    def login(self):
        return login_client(self.client, user=self.user, password=self.password)

    def csrf_token(self):
        return self.client.get(reverse("accounts:csrf-token")).data["csrf_token"]

    def test_refresh_rotates_cookie_and_returns_only_new_access(self):
        login_response = self.login()
        old_refresh = login_response.cookies["refresh_token"].value

        response = self.client.post(
            self.refresh_url,
            {},
            format="json",
            HTTP_X_CSRFTOKEN=self.csrf_token(),
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access", response.data)
        self.assertNotIn("refresh", response.data)
        self.assertNotEqual(response.cookies["refresh_token"].value, old_refresh)
        self.assertEqual(AuthSession.objects.filter(user=self.user).count(), 1)

    def test_refresh_requires_csrf(self):
        self.login()
        response = self.client.post(self.refresh_url, {}, format="json")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_refresh_requires_refresh_cookie(self):
        csrf_token = self.csrf_token()
        response = self.client.post(
            self.refresh_url,
            {},
            format="json",
            HTTP_X_CSRFTOKEN=csrf_token,
        )

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(response.cookies["refresh_token"]["max-age"], 0)

    def test_reused_refresh_cookie_revokes_session(self):
        login_response = self.login()
        old_refresh = login_response.cookies["refresh_token"].value
        csrf_token = self.csrf_token()
        first_refresh = self.client.post(
            self.refresh_url,
            {},
            format="json",
            HTTP_X_CSRFTOKEN=csrf_token,
        )
        self.client.cookies["refresh_token"] = old_refresh

        reused_response = self.client.post(
            self.refresh_url,
            {},
            format="json",
            HTTP_X_CSRFTOKEN=csrf_token,
        )

        self.assertEqual(first_refresh.status_code, status.HTTP_200_OK)
        self.assertEqual(reused_response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertIsNotNone(AuthSession.objects.get(user=self.user).revoked_at)

    def test_password_change_invalidates_refresh_and_revokes_session(self):
        self.login()
        self.user.set_password("Another-Strong-Password-456!")
        self.user.save(update_fields=["password", "password_changed_at"])

        response = self.client.post(
            self.refresh_url,
            {},
            format="json",
            HTTP_X_CSRFTOKEN=self.csrf_token(),
        )

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertIsNotNone(AuthSession.objects.get(user=self.user).revoked_at)
