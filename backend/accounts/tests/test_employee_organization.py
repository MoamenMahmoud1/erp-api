from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db.models.deletion import ProtectedError
from django.test import TestCase

from accounts.models import Employee
from organization.models import Company, Department, Site


User = get_user_model()


class EmployeeOrganizationTests(TestCase):
    def setUp(self):
        self.company = Company.objects.create(name="Test Company")
        self.head_office = self.create_site(
            code="HQ-01",
            site_type=Site.Type.HEAD_OFFICE,
        )
        self.branch = self.create_site(
            code="BR-01",
            site_type=Site.Type.BRANCH,
        )
        self.other_branch = self.create_site(
            code="BR-02",
            site_type=Site.Type.BRANCH,
        )
        self.branch_store = self.create_site(
            code="ST-01",
            site_type=Site.Type.STORE,
            parent=self.branch,
        )

        self.central_department = Department.objects.create(
            company=self.company,
            code="LEGAL",
            name="Legal",
        )
        self.head_office_department = Department.objects.create(
            company=self.company,
            site=self.head_office,
            code="HQ-HR",
            name="Head Office HR",
        )
        self.branch_department = Department.objects.create(
            company=self.company,
            site=self.branch,
            code="BR-HR",
            name="Branch HR",
        )

        self.user_number = 0

    def create_site(self, *, code, site_type, parent=None):
        return Site.objects.create(
            company=self.company,
            parent=parent,
            code=code,
            name=code,
            site_type=site_type,
            address_line_1="Test address",
            city="Cairo",
            country_code="EG",
        )

    def create_employee(self, *, work_site=None, department=None):
        self.user_number += 1
        user = User.objects.create_user(
            username=f"employee-{self.user_number}",
            email=f"employee-{self.user_number}@test.com",
        )
        return Employee.objects.create(
            user=user,
            work_site=work_site,
            department=department,
        )

    def test_employee_may_be_unassigned_during_onboarding(self):
        employee = self.create_employee()

        self.assertIsNone(employee.work_site)
        self.assertIsNone(employee.department)

    def test_central_department_accepts_employee_from_any_site(self):
        employee = self.create_employee(
            work_site=self.branch_store,
            department=self.central_department,
        )

        self.assertEqual(employee.department, self.central_department)

    def test_branch_department_accepts_employee_at_branch(self):
        employee = self.create_employee(
            work_site=self.branch,
            department=self.branch_department,
        )

        self.assertEqual(employee.department, self.branch_department)

    def test_branch_department_accepts_employee_at_child_store(self):
        employee = self.create_employee(
            work_site=self.branch_store,
            department=self.branch_department,
        )

        self.assertEqual(employee.department, self.branch_department)

    def test_site_specific_department_requires_work_site(self):
        with self.assertRaises(ValidationError) as raised:
            self.create_employee(department=self.branch_department)

        self.assertIn("work_site", raised.exception.message_dict)

    def test_employee_cannot_join_department_at_unrelated_site(self):
        with self.assertRaises(ValidationError) as raised:
            self.create_employee(
                work_site=self.other_branch,
                department=self.branch_department,
            )

        self.assertIn("department", raised.exception.message_dict)

    def test_head_office_department_rejects_branch_employee(self):
        with self.assertRaises(ValidationError) as raised:
            self.create_employee(
                work_site=self.branch,
                department=self.head_office_department,
            )

        self.assertIn("department", raised.exception.message_dict)

    def test_assigned_site_and_department_are_protected_from_deletion(self):
        employee = self.create_employee(
            work_site=self.branch,
            department=self.branch_department,
        )

        with self.assertRaises(ProtectedError):
            self.branch.delete()

        with self.assertRaises(ProtectedError):
            self.branch_department.delete()

        self.assertTrue(Employee.objects.filter(pk=employee.pk).exists())
