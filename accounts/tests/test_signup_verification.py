from urllib.parse import parse_qs, urlparse

from django.contrib.auth import authenticate, get_user_model
from django.core import mail
from django.core.cache import cache
from django.test import TestCase, override_settings
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient



@override_settings(
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
    FRONTEND_URL="https://app.example.com",
)
class SignUpVerificationTests(TestCase):
    password = "Strong-Signup-Password-123!"

    def setUp(self):
        cache.clear()
        self.client = APIClient(enforce_csrf_checks=True)
        self.signup_url = reverse("accounts:signup")
        self.verify_url = reverse("accounts:email-verify")
        self.resend_url = reverse("accounts:email-verification-resend")

    def signup(self, **overrides):
        payload = {
            "username": "new-user",
            "email": "New.User@example.com",
            "first_name": "New",
            "last_name": "User",
            "password": self.password,
            "password_confirm": self.password,
        }
        payload.update(overrides)
        with self.captureOnCommitCallbacks(execute=True):
            return self.client.post(self.signup_url, payload, format="json")

    def token_from_latest_email(self):
        verification_url = next(
            line
            for line in mail.outbox[-1].body.splitlines()
            if line.startswith("https://")
        )
        return parse_qs(urlparse(verification_url).query)["token"][0]

    def test_signup_creates_inactive_user_and_sends_verification(self):
        response = self.signup()

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertNotIn("password", response.data)
        user = get_user_model().objects.get(username="new-user")
        self.assertEqual(user.email, "New.User@example.com")
        self.assertFalse(user.is_active)
        self.assertFalse(user.is_verified)
        self.assertTrue(user.check_password(self.password))
        self.assertEqual(mail.outbox[-1].to, [user.email])
        self.assertIsNone(
            authenticate(username=user.email, password=self.password)
        )

    def test_verification_activates_account_and_token_is_single_use(self):
        self.signup()
        token = self.token_from_latest_email()

        first_response = self.client.post(
            self.verify_url,
            {"token": token},
            format="json",
        )
        second_response = self.client.post(
            self.verify_url,
            {"token": token},
            format="json",
        )

        user = get_user_model().objects.get(username="new-user")
        self.assertEqual(first_response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(second_response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertTrue(user.is_active)
        self.assertTrue(user.is_verified)
        self.assertEqual(
            authenticate(username=user.email, password=self.password),
            user,
        )

    def test_resend_rotates_verification_token(self):
        self.signup()
        old_token = self.token_from_latest_email()

        response = self.client.post(
            self.resend_url,
            {"email": "NEW.USER@example.com"},
            format="json",
        )
        new_token = self.token_from_latest_email()
        new_response = self.client.post(
            self.verify_url,
            {"token": new_token},
            format="json",
        )
        old_response = self.client.post(
            self.verify_url,
            {"token": old_token},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertNotEqual(old_token, new_token)
        self.assertEqual(new_response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(old_response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_resend_unknown_email_has_generic_response(self):
        response = self.client.post(
            self.resend_url,
            {"email": "missing@example.com"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(len(mail.outbox), 0)

    def test_signup_rejects_case_insensitive_duplicate_email(self):
        get_user_model().objects.create_user(
            username="existing-user",
            email="existing@example.com",
        )

        response = self.signup(email="EXISTING@example.com")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("email", response.data)

    def test_signup_runs_password_validation(self):
        response = self.signup(password="password", password_confirm="password")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("password", response.data)
