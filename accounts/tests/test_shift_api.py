from decimal import Decimal

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from accounts.models import Employee, EmployeeShift, Role
from organization.models import Company, Site


User = get_user_model()


class EmployeeShiftAPITests(TestCase):
    def setUp(self):
        self.company = Company.objects.create(name="Test Company")
        self.site = Site.objects.create(
            company=self.company,
            code="ST-01",
            name="Store 01",
            site_type=Site.Type.STORE,
            address_line_1="Address",
            city="Cairo",
            country_code="EG",
        )
        self.user = User.objects.create_user(username="shift-user", email="shift@test.com", password="StrongPass123!")
        group = Group.objects.create(name="Test Shift Role")
        role = Role.objects.create(group=group, code="test-shift-role", level=20, scope=Role.Scope.SITE, requires_shift=True)
        self.user.groups.add(group)
        permission = Permission.objects.get(codename="start_employee_shift", content_type__app_label="accounts")
        close_permission = Permission.objects.get(codename="close_employee_shift", content_type__app_label="accounts")
        self.user.user_permissions.add(permission, close_permission)
        self.employee = Employee.objects.create(user=self.user, work_site=self.site)
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def test_start_shift_uses_employee_site(self):
        response = self.client.post(reverse("accounts:shift-start"), {"opening_cash": "100.00"}, format="json")
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["site"], self.site.pk)
        self.assertEqual(response.data["status"], "open")
        self.assertEqual(EmployeeShift.objects.get(employee=self.employee).opening_cash, Decimal("100.00"))

    def test_current_user_exposes_role_site_and_shift_context(self):
        start = self.client.post(reverse("accounts:shift-start"), {"opening_cash": "100.00"}, format="json")
        self.assertEqual(start.status_code, 201)

        response = self.client.get(reverse("accounts:current-user"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["role"]["code"], "test-shift-role")
        self.assertEqual(response.data["employee"]["site"]["id"], self.site.pk)
        self.assertEqual(response.data["current_shift"]["id"], start.data["id"])

    def test_close_shift_returns_reconciliation_values(self):
        self.client.post(reverse("accounts:shift-start"), {"opening_cash": "100.00"}, format="json")
        response = self.client.post(
            reverse("accounts:shift-close"),
            {"closing_cash": "100.00", "closing_transfer": "0.00"},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["cash_difference"], "0.00")
        self.assertEqual(response.data["transfer_difference"], "0.00")
        self.assertEqual(response.data["status"], "closed")
