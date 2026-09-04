import uuid

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from authsession.http import ClientContext
from authsession.models import AuthSession
from authsession.services import start_auth_session


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
        self.client = APIClient(enforce_csrf_checks=True)
        csrf_response = self.client.get(reverse("accounts:csrf-token"))
        self.csrf_token = csrf_response.data["csrf_token"]
        self.device_id = uuid.uuid4()
        self.login_response = self.client.post(
            reverse("accounts:login"),
            {"identifier": self.user.email, "password": self.password},
            format="json",
            HTTP_X_CSRFTOKEN=self.csrf_token,
            HTTP_X_DEVICE_ID=str(self.device_id),
        )
        # Login sets the httponly refresh_token and signed device_id cookies
        # on the test client (path=/api/v1/auth/), which the authsession
        # permission reads for its stateful session verification.
        self.client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {self.login_response.data['access']}"
        )
        self.refresh_token = self.login_response.cookies.get("refresh_token")

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
        self.assertEqual(
            sum(item["is_current"] for item in response.data["results"]),
            1,
        )
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
        self.assertIsNotNone(
            AuthSession.objects.get(pk=second.session_id).revoked_at
        )

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
