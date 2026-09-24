from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient


class AdminAccessTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.superuser = User.objects.create_superuser(
            username="admin",
            email="admin@example.com",
            password="StrongAdminPassword123!",
        )
        self.staff_user = User.objects.create_user(
            username="staff",
            email="staff@example.com",
            password="StrongStaffPassword123!",
            is_staff=True,
        )

    def test_anonymous_cannot_reach_admin(self):
        response = self.client.get("/admin/")
        self.assertEqual(response.status_code, 404)

    def test_staff_without_superuser_cannot_reach_admin(self):
        self.client.force_login(self.staff_user)
        response = self.client.get("/admin/")
        self.assertEqual(response.status_code, 404)

    def test_superuser_can_reach_admin(self):
        self.client.force_login(self.superuser)
        response = self.client.get("/admin/")
        self.assertEqual(response.status_code, 200)


class AdminSessionBridgeTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.superuser = User.objects.create_superuser(
            username="admin",
            email="admin@example.com",
            password="StrongAdminPassword123!",
        )
        self.staff_user = User.objects.create_user(
            username="staff",
            email="staff@example.com",
            password="StrongStaffPassword123!",
        )
        self.client = APIClient()

    def test_anonymous_cannot_create_admin_session(self):
        response = self.client.post("/api/v1/auth/admin/session/", {})
        self.assertEqual(response.status_code, 401)

    def test_non_superuser_cannot_create_admin_session(self):
        self.client.force_authenticate(user=self.staff_user)
        response = self.client.post("/api/v1/auth/admin/session/", {})
        self.assertEqual(response.status_code, 403)

    def test_superuser_gets_django_admin_session(self):
        self.client.force_authenticate(user=self.superuser)
        response = self.client.post("/api/v1/auth/admin/session/", {})
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data["url"].endswith("/admin/"))

        self.client.force_authenticate(user=None)
        admin_response = self.client.get("/admin/")
        self.assertEqual(admin_response.status_code, 200)

    def test_erp_logout_clears_admin_session(self):
        self.client.force_login(self.superuser)
        session_response = self.client.post("/api/v1/auth/admin/session/", {})
        self.assertEqual(session_response.status_code, 200)

        self.client.force_authenticate(user=self.superuser)
        logout_response = self.client.post("/api/v1/auth/logout/", {})
        self.assertEqual(logout_response.status_code, 204)

        self.client.force_authenticate(user=None)
        admin_response = self.client.get("/admin/")
        self.assertEqual(admin_response.status_code, 404)
