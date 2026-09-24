from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.test import TestCase


class UserIdentityConstraintTests(TestCase):
    def test_user_manager_requires_email(self):
        with self.assertRaises(ValueError):
            get_user_model().objects.create_user(
                username="missing-email",
                email="",
                password="Strong-Test-Password-123!",
            )

    def test_username_cannot_contain_at_sign(self):
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                get_user_model().objects.create_user(
                    username="ahmed@example.com",
                    email="another@example.com",
                    password="Strong-Test-Password-123!",
                )

    def test_email_is_unique_case_insensitively(self):
        UserModel = get_user_model()
        UserModel.objects.create_user(
            username="first-user",
            email="Ahmed@example.com",
            password="Strong-Test-Password-123!",
        )

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                UserModel.objects.create_user(
                    username="second-user",
                    email="ahmed@example.com",
                    password="Strong-Test-Password-456!",
                )
