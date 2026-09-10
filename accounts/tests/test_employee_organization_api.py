from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from accounts.models import Employee, GroupPolicy
from organization.models import Company, Department, Site


User = get_user_model()


def create_role(*, code, level, permissions, scope=GroupPolicy.Scope.SITE, requires_shift=False):
    group = Group.objects.create(name=f"Test {code.title()}")
    policy = GroupPolicy.objects.create(
        group=group,
        level=level,
        scope=scope,
        requires_shift=requires_shift,
    )
    group.permissions.set(
        Permission.objects.filter(
            content_type__app_label="accounts",
            content_type__model="employee",
            codename__in=permissions,
        )
    )
    return policy


class EmployeeOrganizationAPITests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.company = Company.objects.create(name="Test Company")
        cls.branch = cls.create_site(code="BR-01", site_type=Site.Type.BRANCH)
        cls.other_branch = cls.create_site(code="BR-02", site_type=Site.Type.BRANCH)
        cls.branch_department = Department.objects.create(company=cls.company, site=cls.branch, code="BR-HR", name="Branch HR")
        cls.other_department = Department.objects.create(company=cls.company, site=cls.other_branch, code="BR2-HR", name="Other Branch HR")

        cls.admin_role = create_role(
            code="organization-admin",
            level=80,
            permissions=("add_employee", "change_employee", "view_employee"),
        )
        cls.employee_role = create_role(
            code="organization-employee",
            level=10,
            permissions=("view_employee",),
        )
        cls.secondary_role = create_role(
            code="organization-supervisor",
            level=30,
            permissions=("view_employee",),
        )
        cls.unconfigured_role = Group.objects.create(name="Custom Role Without Policy")

        cls.actor_user = User.objects.create_user(username="organization-admin", email="organization-admin@test.com")
        cls.actor_user.groups.add(cls.admin_role.group)
        cls.actor = Employee.objects.create(user=cls.actor_user, work_site=cls.branch, department=cls.branch_department)

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
        user = User.objects.create_user(username=f"target-{suffix}", email=f"target-{suffix}@test.com")
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
        self.assertEqual(response.data["department"], self.branch_department.pk)
        employee = Employee.objects.get(user=target_user)
        self.assertEqual(employee.work_site, self.branch)
        self.assertEqual(employee.department, self.branch_department)

    def test_employee_list_returns_roles_and_organization_details(self):
        target_user = self.create_target_user(suffix="details")
        target_user.groups.add(self.secondary_role.group)
        employee = Employee.objects.create(user=target_user, manager=self.actor, work_site=self.branch, department=self.branch_department)
        response = self.client.get(self.employee_list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        row = next(item for item in response.data["results"] if item["id"] == employee.pk)
        self.assertEqual(row["user_details"]["role"]["name"], self.secondary_role.group.name)
        self.assertEqual(
            {role["name"] for role in row["user_details"]["roles"]},
            {self.employee_role.group.name, self.secondary_role.group.name},
        )
        self.assertEqual(row["work_site_details"]["id"], self.branch.pk)
        self.assertEqual(row["work_site_details"]["code"], self.branch.code)
        self.assertEqual(row["department_details"]["id"], self.branch_department.pk)
        self.assertEqual(row["department_details"]["code"], self.branch_department.code)

    def test_employee_options_returns_user_roles(self):
        target_user = self.create_target_user(suffix="options")
        target_user.groups.add(self.secondary_role.group)
        response = self.client.get(reverse("accounts:employee-options"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        row = next(item for item in response.data["results"] if item["id"] == target_user.pk)
        self.assertEqual(row["role"]["name"], self.secondary_role.group.name)
        self.assertEqual(
            {role["name"] for role in row["roles"]},
            {self.employee_role.group.name, self.secondary_role.group.name},
        )

    def test_employee_groups_endpoint_returns_assignable_groups(self):
        response = self.client.get(reverse("accounts:employee-groups"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        groups = {item["id"]: item for item in response.data["results"]}
        self.assertIn(self.employee_role.group.pk, groups)
        self.assertIn(self.secondary_role.group.pk, groups)
        self.assertNotIn(self.admin_role.group.pk, groups)
        self.assertEqual(groups[self.secondary_role.group.pk]["role"]["name"], self.secondary_role.group.name)

    def test_roles_endpoint_returns_groups_as_roles(self):
        response = self.client.get(reverse("accounts:role-list"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        roles = {item["id"]: item for item in response.data["results"]}
        self.assertIn(self.employee_role.group.pk, roles)
        self.assertIn(self.secondary_role.group.pk, roles)
        self.assertIn(self.unconfigured_role.pk, roles)
        self.assertNotIn(self.admin_role.group.pk, roles)
        self.assertEqual(roles[self.secondary_role.group.pk]["name"], self.secondary_role.group.name)
        self.assertEqual(roles[self.unconfigured_role.pk]["level"], 0)
        self.assertEqual(roles[self.unconfigured_role.pk]["scope"], GroupPolicy.Scope.SITE)
        self.assertFalse(roles[self.unconfigured_role.pk]["requires_shift"])

    def test_create_and_update_employee_role_directly(self):
        target_user = self.create_target_user(suffix="direct-role")
        response = self.client.post(
            self.employee_list_url,
            {
                "user": target_user.pk,
                "manager": self.actor.pk,
                "work_site": self.branch.pk,
                "department": self.branch_department.pk,
                "role_id": self.secondary_role.group.pk,
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["role"]["id"], self.secondary_role.group.pk)
        target_user.refresh_from_db()
        self.assertTrue(target_user.groups.filter(pk=self.secondary_role.group.pk).exists())
        self.assertFalse(target_user.groups.filter(pk=self.employee_role.group.pk).exists())
        employee = Employee.objects.get(user=target_user)

        response = self.client.patch(
            reverse("accounts:employee-detail", kwargs={"pk": employee.pk}),
            {"role_id": self.employee_role.group.pk},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["role"]["id"], self.employee_role.group.pk)
        target_user.refresh_from_db()
        self.assertTrue(target_user.groups.filter(pk=self.employee_role.group.pk).exists())
        self.assertFalse(target_user.groups.filter(pk=self.secondary_role.group.pk).exists())

        response = self.client.patch(
            reverse("accounts:employee-detail", kwargs={"pk": employee.pk}),
            {"role_id": None},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsNone(response.data["role"])
        target_user.refresh_from_db()
        self.assertFalse(target_user.groups.filter(pk=self.employee_role.group.pk).exists())

    def test_create_and_update_employee_groups(self):
        target_user = self.create_target_user(suffix="groups")
        response = self.client.post(
            self.employee_list_url,
            {
                "user": target_user.pk,
                "manager": self.actor.pk,
                "work_site": self.branch.pk,
                "department": self.branch_department.pk,
                "group_ids": [self.secondary_role.group.pk],
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual({group["id"] for group in response.data["groups"]}, {self.secondary_role.group.pk})
        target_user.refresh_from_db()
        self.assertTrue(target_user.groups.filter(pk=self.secondary_role.group.pk).exists())
        self.assertFalse(target_user.groups.filter(pk=self.employee_role.group.pk).exists())
        employee = Employee.objects.get(user=target_user)
        response = self.client.patch(reverse("accounts:employee-detail", kwargs={"pk": employee.pk}), {"group_ids": []}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        target_user.refresh_from_db()
        self.assertFalse(target_user.groups.filter(pk=self.secondary_role.group.pk).exists())
        self.assertEqual(response.data["groups"], [])

    def test_create_employee_rejects_equal_or_higher_group_role(self):
        target_user = self.create_target_user(suffix="elevated")
        response = self.client.post(
            self.employee_list_url,
            {
                "user": target_user.pk,
                "manager": self.actor.pk,
                "work_site": self.branch.pk,
                "department": self.branch_department.pk,
                "group_ids": [self.admin_role.group.pk],
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("group_ids", response.data)
        self.assertFalse(Employee.objects.filter(user=target_user).exists())

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
        employee = Employee.objects.create(user=target_user, manager=self.actor, work_site=self.branch, department=self.branch_department)
        response = self.client.patch(
            reverse("accounts:employee-detail", kwargs={"pk": employee.pk}),
            {"work_site": self.other_branch.pk},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("department", response.data)
        employee.refresh_from_db()
        self.assertEqual(employee.work_site, self.branch)
        self.assertEqual(employee.department, self.branch_department)
