from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.test import APIRequestFactory

from accounts.api.serializers.login import LoginSerializer


class LoginSerializerTests(TestCase):
    password = "Strong-Test-Password-123!"

    @classmethod
    def setUpTestData(cls):
        cls.user = get_user_model().objects.create_user(
            username="ahmed",
            email="Ahmed@example.com",
            password=cls.password,
        )

    def setUp(self):
        self.request = APIRequestFactory().post("/api/v1/auth/login/")

    def make_serializer(self, data):
        return LoginSerializer(
            data=data,
            context={"request": self.request},
        )

    def test_exposes_only_identifier_and_password_as_input_fields(self):
        serializer = self.make_serializer(data={})

        self.assertEqual(set(serializer.fields), {"identifier", "password"})

    def test_authenticates_with_email_and_issues_token_pair(self):
        serializer = self.make_serializer(
            data={
                "identifier": "  AHMED@EXAMPLE.COM  ",
                "password": self.password,
            }
        )

        serializer.is_valid(raise_exception=True)

        self.assertEqual(serializer.user, self.user)
        self.assertEqual(serializer.validated_data, {})

    def test_authenticates_with_username_and_issues_token_pair(self):
        serializer = self.make_serializer(
            data={
                "identifier": self.user.username,
                "password": self.password,
            }
        )

        serializer.is_valid(raise_exception=True)

        self.assertEqual(serializer.user, self.user)
        self.assertEqual(serializer.validated_data, {})

    def test_rejects_wrong_password_with_generic_error_code(self):
        serializer = self.make_serializer(
            data={
                "identifier": self.user.email,
                "password": "Wrong-Password-123!",
            }
        )

        with self.assertRaises(AuthenticationFailed) as raised:
            serializer.is_valid(raise_exception=True)

        self.assertEqual(raised.exception.get_codes(), "no_active_account")

    def test_rejects_inactive_user(self):
        self.user.is_active = False
        self.user.save(update_fields=["is_active"])
        serializer = self.make_serializer(
            data={
                "identifier": self.user.email,
                "password": self.password,
            }
        )

        with self.assertRaises(AuthenticationFailed) as raised:
            serializer.is_valid(raise_exception=True)

        self.assertEqual(raised.exception.get_codes(), "no_active_account")

    def test_rejects_username_request_key(self):
        serializer = self.make_serializer(
            data={
                "username": self.user.username,
                "password": self.password,
            }
        )

        self.assertFalse(serializer.is_valid())
        self.assertEqual(serializer.errors["identifier"][0].code, "required")
