from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.test import RequestFactory, TestCase

from accounting.permissions import AccountingReportPermission
from common.permissions import ModelAccessPermission
from products.api.views import ProductViewSet


class PermissionPolicyTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="user", email="user@example.com", password="pass")
        self.factory = RequestFactory()

    def test_product_requires_view_permission(self):
        request = self.factory.get("/api/v1/products/")
        request.user = self.user
        view = ProductViewSet()
        view.request = request
        self.assertFalse(ModelAccessPermission().has_permission(request, view))

        permission = Permission.objects.get(codename="view_product")
        self.user.user_permissions.add(permission)
        self.assertTrue(ModelAccessPermission().has_permission(request, view))

    def test_financial_reports_require_explicit_permission(self):
        request = self.factory.get("/api/v1/accounting/reports/")
        request.user = self.user
        view = object()
        self.assertFalse(AccountingReportPermission().has_permission(request, view))
        permission = Permission.objects.get(codename="view_financial_reports", content_type__app_label="accounting")
        self.user.user_permissions.add(permission)
        self.assertTrue(AccountingReportPermission().has_permission(request, view))
