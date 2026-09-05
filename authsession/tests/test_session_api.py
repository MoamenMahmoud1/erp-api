import uuid

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework import status

from authsession.http import ClientContext
from authsession.models import AuthSession
from authsession.services import start_auth_session
from core.testing.auth import login_client, new_api_client


class AuthSessionApiTests(TestCase):
    password = "Strong-Test-Password-123!"

    @classmethod
    def setUpTestData(cls):
        cls.user = get_user_model().objects.create_user(
            username="session-user",
            email="session-user@example.com",
            password=cls.password,
        )
        cls.other_user = get_user_model().objects.create_user(
            username="other-session-user",
            email="other-session-user@example.com",
            password=cls.password,
        )

    def setUp(self):
        self.client = new_api_client()
        login_client(self.client, user=self.user, password=self.password)

    def test_user_can_list_active_devices_and_identify_current_device(self):
        start_auth_session(
            user=self.user,
            client_context=ClientContext(
                device_id=uuid.uuid4(),
                device_name="Second device",
                user_agent="Test Browser/2.0",
                ip_address="198.51.100.9",
            ),
        )

        response = self.client.get(reverse("accounts:session-list"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 2)
        self.assertEqual(sum(item["is_current"] for item in response.data["results"]), 1)
        self.assertIn("no-store", response["Cache-Control"])

    def test_user_can_revoke_another_device(self):
        second = start_auth_session(
            user=self.user,
            client_context=ClientContext(
                device_id=uuid.uuid4(),
                device_name="Second device",
                user_agent="Test Browser/2.0",
                ip_address="198.51.100.9",
            ),
        )

        response = self.client.delete(
            reverse("accounts:session-detail", args=(second.session_id,)),
        )

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertIsNotNone(AuthSession.objects.get(pk=second.session_id).revoked_at)

    def test_revoked_current_session_cannot_manage_devices(self):
        AuthSession.objects.filter(
            user=self.user,
            revoked_at__isnull=True,
        ).update(revoked_at=timezone.now())

        response = self.client.get(reverse("accounts:session-list"))
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_user_cannot_access_another_users_session(self):
        other = start_auth_session(
            user=self.other_user,
            client_context=ClientContext(
                device_id=uuid.uuid4(),
                device_name="Other device",
                user_agent="Test Browser/3.0",
                ip_address="203.0.113.9",
            ),
        )

        response = self.client.get(
            reverse("accounts:session-detail", args=(other.session_id,))
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
