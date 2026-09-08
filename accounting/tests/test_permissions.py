from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.test import RequestFactory, TestCase

from accounting.permissions import AccountingModelPermission, AccountingReportPermission
from common.permissions import ModelAccessPermission
from invoices.permissions import InvoicePermission
from products.api.views import ProductViewSet


class PermissionPolicyTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="user",
            email="user@example.com",
            password="pass",
        )
        self.factory = RequestFactory()

    def _grant(self, app_label, codename):
        permission = Permission.objects.get(
            codename=codename,
            content_type__app_label=app_label,
        )
        self.user.user_permissions.add(permission)

    def test_product_requires_view_permission(self):
        request = self.factory.get("/api/v1/products/")
        request.user = self.user
        view = ProductViewSet()
        view.request = request
        self.assertFalse(ModelAccessPermission().has_permission(request, view))

        self._grant("products", "view_product")
        self.assertTrue(ModelAccessPermission().has_permission(request, view))

    def test_invoice_list_requires_view_permission(self):
        request = self.factory.get("/api/v1/invoices/")
        request.user = self.user
        view = type("View", (), {"action": "list"})()

        self.assertFalse(InvoicePermission().has_permission(request, view))
        self._grant("invoices", "view_invoice")
        self.assertTrue(InvoicePermission().has_permission(request, view))

    def test_invoice_confirm_requires_explicit_permission(self):
        request = self.factory.post("/api/v1/invoices/1/confirm/")
        request.user = self.user
        view = type("View", (), {"action": "confirm"})()

        self.assertFalse(InvoicePermission().has_permission(request, view))
        self._grant("invoices", "confirm_invoice")
        self.assertTrue(InvoicePermission().has_permission(request, view))

    def test_invoice_create_requires_add_permission(self):
        request = self.factory.post("/api/v1/invoices/")
        request.user = self.user
        view = type("View", (), {"action": "create"})()

        self.assertFalse(InvoicePermission().has_permission(request, view))
        self._grant("invoices", "add_invoice")
        self.assertTrue(InvoicePermission().has_permission(request, view))

    def test_chart_of_accounts_write_requires_management_permission(self):
        request = self.factory.post("/api/v1/accounting/accounts/")
        request.user = self.user
        view = type("View", (), {"write_permission_codename": "accounting.manage_chart_of_accounts"})()

        self.assertFalse(AccountingModelPermission().has_permission(request, view))
        self._grant("accounting", "manage_chart_of_accounts")
        self.assertTrue(AccountingModelPermission().has_permission(request, view))

    def test_financial_reports_require_explicit_permission(self):
        request = self.factory.get("/api/v1/accounting/reports/")
        request.user = self.user
        view = object()
        self.assertFalse(AccountingReportPermission().has_permission(request, view))
        self._grant("accounting", "view_financial_reports")
        self.assertTrue(AccountingReportPermission().has_permission(request, view))
