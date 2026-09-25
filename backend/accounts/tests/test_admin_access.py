from django.contrib.auth import get_user_model
from django.test import Client, RequestFactory, TestCase
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

    def test_superuser_can_delete_another_user(self):
        target = get_user_model().objects.create_user(
            username="target",
            email="target@example.com",
            password="StrongTargetPassword123!",
        )
        self.client.force_login(self.superuser)
        response = self.client.post(
            f"/admin/accounts/customusermodel/{target.pk}/delete/",
            {"post": "yes"},
        )
        self.assertEqual(response.status_code, 302)
        self.assertFalse(get_user_model().objects.filter(pk=target.pk).exists())

    def test_superuser_can_delete_themselves(self):
        from django.contrib import admin as django_admin

        model_admin = django_admin.site._registry[get_user_model()]
        request = RequestFactory().get("/admin/")
        request.user = self.superuser

        self.assertTrue(model_admin.has_delete_permission(request, self.superuser))

    def test_superuser_can_delete_user_with_auth_sessions(self):
        from authsession.models import AuthSession
        from django.contrib import admin as django_admin
        from django.utils import timezone
        import uuid
        from datetime import timedelta

        target = get_user_model().objects.create_user(
            username="cascade-target",
            email="cascade-target@example.com",
            password="StrongTargetPassword123!",
        )
        AuthSession.objects.create(
            user=target,
            device_id=uuid.uuid4(),
            current_refresh_jti=uuid.uuid4(),
            expires_at=timezone.now() + timedelta(days=30),
        )

        model_admin = django_admin.site._registry[get_user_model()]
        request = RequestFactory().get("/admin/")
        request.user = self.superuser

        _deleted_objects, _model_count, perms_needed, protected = model_admin.get_deleted_objects(
            get_user_model().objects.filter(pk=target.pk),
            request,
        )

        self.assertNotIn(AuthSession._meta.verbose_name, perms_needed)
        self.assertFalse(protected)


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
        from accounting.models.journal import JournalEntry
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
            JournalEntry,
        )
        for model in hidden_models:
            self.assertNotIn(model, django_admin.site._registry)

    def test_internal_models_remain_available_in_admin(self):
        from django.contrib import admin as django_admin
        from authsession.models import AuthSession
        from customer_assignments.models import CustomerAssignment
        from inventory.models import StockMovementItem, StockTransferRequest
        from accounts.models import RoleProfile

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
