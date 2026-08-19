from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from accounts.models import Employee, Role
from organization.models import Company, Department, Site


User = get_user_model()


def create_role(*, code, level, permissions):
    group = Group.objects.create(name=f"Test {code.title()}")
    role = Role.objects.create(
        group=group,
        code=code,
        level=level,
    )
    group.permissions.set(
        Permission.objects.filter(
            content_type__app_label="accounts",
            content_type__model="employee",
            codename__in=permissions,
        )
    )
    return role


class EmployeeOrganizationAPITests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.company = Company.objects.create(name="Test Company")
        cls.branch = cls.create_site(
            code="BR-01",
            site_type=Site.Type.BRANCH,
        )
        cls.other_branch = cls.create_site(
            code="BR-02",
            site_type=Site.Type.BRANCH,
        )
        cls.branch_department = Department.objects.create(
            company=cls.company,
            site=cls.branch,
            code="BR-HR",
            name="Branch HR",
        )
        cls.other_department = Department.objects.create(
            company=cls.company,
            site=cls.other_branch,
            code="BR2-HR",
            name="Other Branch HR",
        )

        cls.admin_role = create_role(
            code="organization-admin",
            level=80,
            permissions=(
                "add_employee",
                "change_employee",
                "view_employee",
            ),
        )
        cls.employee_role = create_role(
            code="organization-employee",
            level=10,
            permissions=("view_employee",),
        )

        cls.actor_user = User.objects.create_user(
            username="organization-admin",
            email="organization-admin@test.com",
        )
        cls.actor_user.groups.add(cls.admin_role.group)
        cls.actor = Employee.objects.create(
            user=cls.actor_user,
            work_site=cls.branch,
            department=cls.branch_department,
        )

    @classmethod
    def create_site(cls, *, code, site_type):
        return Site.objects.create(
            company=cls.company,
            code=code,
            name=code,
            site_type=site_type,
            address_line_1="Test address",
            city="Cairo",
            country_code="EG",
        )

    def setUp(self):
        self.client = APIClient()
        self.client.force_authenticate(self.actor_user)
        self.employee_list_url = reverse("accounts:employee-list")

    def create_target_user(self, *, suffix):
        user = User.objects.create_user(
            username=f"target-{suffix}",
            email=f"target-{suffix}@test.com",
        )
        user.groups.add(self.employee_role.group)
        return user

    def test_create_employee_with_work_site_and_department(self):
        target_user = self.create_target_user(suffix="valid")

        response = self.client.post(
            self.employee_list_url,
            {
                "user": target_user.pk,
                "manager": self.actor.pk,
                "work_site": self.branch.pk,
                "department": self.branch_department.pk,
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["work_site"], self.branch.pk)
        self.assertEqual(
            response.data["department"],
            self.branch_department.pk,
        )

        employee = Employee.objects.get(user=target_user)
        self.assertEqual(employee.work_site, self.branch)
        self.assertEqual(employee.department, self.branch_department)

    def test_create_rejects_department_from_unrelated_site(self):
        target_user = self.create_target_user(suffix="invalid")

        response = self.client.post(
            self.employee_list_url,
            {
                "user": target_user.pk,
                "manager": self.actor.pk,
                "work_site": self.branch.pk,
                "department": self.other_department.pk,
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("department", response.data)
        self.assertFalse(Employee.objects.filter(user=target_user).exists())

    def test_partial_update_validates_existing_department_against_new_site(self):
        target_user = self.create_target_user(suffix="patch")
        employee = Employee.objects.create(
            user=target_user,
            manager=self.actor,
            work_site=self.branch,
            department=self.branch_department,
        )

        response = self.client.patch(
            reverse(
                "accounts:employee-detail",
                kwargs={"pk": employee.pk},
            ),
            {"work_site": self.other_branch.pk},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("department", response.data)

        employee.refresh_from_db()
        self.assertEqual(employee.work_site, self.branch)
        self.assertEqual(employee.department, self.branch_department)
