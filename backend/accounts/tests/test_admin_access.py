from django.contrib.auth import get_user_model
from django.test import Client, TestCase
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
        self.admin_browser = Client()
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

        self.admin_browser.cookies.update(self.client.cookies)
        admin_response = self.admin_browser.get("/admin/")
        self.assertEqual(admin_response.status_code, 200)

    def test_erp_logout_clears_admin_session(self):
        self.client.force_authenticate(user=self.superuser)
        session_response = self.client.post("/api/v1/auth/admin/session/", {})
        self.assertEqual(session_response.status_code, 200)
        self.admin_browser.cookies.update(self.client.cookies)

        self.client.force_authenticate(user=self.superuser)
        logout_response = self.client.post("/api/v1/auth/logout/", {})
        self.assertEqual(logout_response.status_code, 204)

        admin_response = self.admin_browser.get("/admin/")
        self.assertEqual(admin_response.status_code, 404)


class AdminModelSurfaceTests(TestCase):
    def test_frontend_managed_models_are_not_registered_in_admin(self):
        from django.contrib import admin as django_admin
        from inventory.models import StockBalance, StockBatchBalance, StockLocation, StockMovement
        from organization.models import Department, Site
        from accounts.models import Employee
        from products.models import Product, CartonPricing
        from customers.models import Customer
        from suppliers.models import Supplier

        hidden_models = (
            Employee,
            Product,
            CartonPricing,
            Customer,
            Supplier,
            Site,
            Department,
            StockLocation,
            StockBalance,
            StockBatchBalance,
            StockMovement,
        )
        for model in hidden_models:
            self.assertNotIn(model, django_admin.site._registry)

    def test_internal_models_remain_available_in_admin(self):
        from django.contrib import admin as django_admin
        from authsession.models import AuthSession
        from customer_assignments.models import CustomerAssignment
        from inventory.models import StockMovementItem, StockTransferRequest
        from accounts.models import RoleProfile
        from django.contrib.auth import get_user_model

        visible_models = (
            get_user_model(),
            RoleProfile,
            AuthSession,
            CustomerAssignment,
            StockTransferRequest,
            StockMovementItem,
        )
        for model in visible_models:
            self.assertIn(model, django_admin.site._registry)
