from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase

from accounts.models import Employee
from organization.models import Company, Site
from services.organization_scope import visible_site_ids


class BranchScopeTests(TestCase):
    def setUp(self):
        self.company = Company.objects.create(name="Test Company")
        self.head_office = Site.objects.create(
            company=self.company,
            code="HQ",
            name="Head Office",
            site_type=Site.Type.HEAD_OFFICE,
            address_line_1="HQ",
            city="Cairo",
            country_code="EG",
        )
        self.branch_a = Site.objects.create(
            company=self.company,
            code="BR-A",
            name="Branch A",
            site_type=Site.Type.BRANCH,
            address_line_1="A",
            city="Cairo",
            country_code="EG",
        )
        self.store_a = Site.objects.create(
            company=self.company,
            code="ST-A",
            name="Store A",
            site_type=Site.Type.STORE,
            parent=self.branch_a,
            address_line_1="A Store",
            city="Cairo",
            country_code="EG",
        )
        self.branch_b = Site.objects.create(
            company=self.company,
            code="BR-B",
            name="Branch B",
            site_type=Site.Type.BRANCH,
            address_line_1="B",
            city="Cairo",
            country_code="EG",
        )

    def make_user(self, username):
        return get_user_model().objects.create_user(
            username=username,
            email=f"{username}@example.com",
            password="StrongPass123!",
        )

    def test_branch_employee_sees_branch_and_child_store_only(self):
        user = self.make_user("branch-user")
        Employee.objects.create(user=user, work_site=self.branch_a)

        visible = set(Site.objects.filter(pk__in=visible_site_ids(user)).values_list("pk", flat=True))
        self.assertEqual(visible, {self.branch_a.pk, self.store_a.pk})
        self.assertNotIn(self.branch_b.pk, visible)
        self.assertNotIn(self.head_office.pk, visible)

    def test_store_employee_sees_only_own_store(self):
        user = self.make_user("store-user")
        Employee.objects.create(user=user, work_site=self.store_a)

        visible = set(Site.objects.filter(pk__in=visible_site_ids(user)).values_list("pk", flat=True))
        self.assertEqual(visible, {self.store_a.pk})

    def test_cross_branch_manager_assignment_is_rejected(self):
        manager_user = self.make_user("manager")
        employee_user = self.make_user("employee")
        manager = Employee.objects.create(user=manager_user, work_site=self.branch_a)
        employee = Employee(user=employee_user, work_site=self.branch_b, manager=manager)

        with self.assertRaises(ValidationError):
            employee.full_clean()
