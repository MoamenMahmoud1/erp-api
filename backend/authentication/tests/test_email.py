from django.contrib.auth import authenticate, get_user_model
from django.test import TestCase


class EmailBackendTests(TestCase):
    password = "Strong-Test-Password-123!"

    @classmethod
    def setUpTestData(cls):
        cls.user = get_user_model().objects.create_user(
            username="ahmed",
            email="Ahmed@example.com",
            password=cls.password,
        )

    def test_authenticates_with_email_case_insensitively(self):
        authenticated_user = authenticate(
            username="  AHMED@EXAMPLE.COM  ",
            password=self.password,
        )

        self.assertEqual(authenticated_user, self.user)
        self.assertEqual(
            authenticated_user.backend,
            "authentication.email.EmailBackend",
        )

    def test_username_falls_back_to_django_model_backend(self):
        authenticated_user = authenticate(
            username=self.user.username,
            password=self.password,
        )

        self.assertEqual(authenticated_user, self.user)
        self.assertEqual(
            authenticated_user.backend,
            "django.contrib.auth.backends.ModelBackend",
        )

    def test_rejects_wrong_password_for_existing_email(self):
        authenticated_user = authenticate(
            username=self.user.email,
            password="Wrong-Password-123!",
        )

        self.assertIsNone(authenticated_user)

    def test_rejects_unknown_email(self):
        authenticated_user = authenticate(
            username="missing@example.com",
            password=self.password,
        )

        self.assertIsNone(authenticated_user)

    def test_rejects_inactive_user(self):
        self.user.is_active = False
        self.user.save(update_fields=["is_active"])

        authenticated_user = authenticate(
            username=self.user.email,
            password=self.password,
        )

        self.assertIsNone(authenticated_user)
