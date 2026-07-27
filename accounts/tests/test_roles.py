from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.core.exceptions import ValidationError
from django.db import connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

from accounts.models import Employee, Role

User = get_user_model()


def create_role(*, code, level, permissions=()):
    group = Group.objects.create(name=f"Test {code.title()}")
    role = Role.objects.create(group=group, code=code, level=level)

    if permissions:
        group.permissions.set(
            Permission.objects.filter(
                content_type__app_label="accounts",
                content_type__model="employee",
                codename__in=permissions,
            )
        )

    return role


class RoleHierarchyTests(TestCase):
    def setUp(self):
        self.admin_role = create_role(code="admin", level=80)
        self.employee_role = create_role(code="employee", level=10)
        self.admin = User.objects.create_user(username="admin", email="admin@test.com")
        self.employee = User.objects.create_user(username="employee", email="employee@test.com")
        self.admin.groups.set([self.admin_role.group])
        self.employee.groups.set([self.employee_role.group])

    def test_higher_role_can_manage_lower_role(self):
        self.assertTrue(Role.can_manage_user(self.admin, self.employee))

    def test_lower_role_can_not_manage_higher_role(self):
        self.assertFalse(Role.can_manage_user(self.employee, self.admin))

    def test_new_user_does_not_receive_an_implicit_role(self):
        user = User.objects.create_user(username="new-user", email="new-user@test.com")

        self.assertFalse(user.groups.exists())

    def test_unauthenticated_actor_can_not_manage_users(self):
        self.assertFalse(Role.can_manage_user(None, self.employee))


class EmployeeVisibilityTests(APITestCase):
    def setUp(self):
        self.manager_role = create_role(
            code="manager",
            level=40,
            permissions=("add_employee", "change_employee", "view_employee"),
        )
        self.employee_role = create_role(
            code="employee",
            level=10,
            permissions=("view_employee",),
        )

        self.manager_user = User.objects.create_user(username="manager", email="manager@test.com")
        self.child_user = User.objects.create_user(username="child", email="child@test.com")
        self.grandchild_user = User.objects.create_user(
            username="grandchild",
            email="grandchild@test.com",
        )
        self.other_user = User.objects.create_user(username="other", email="other@test.com")

        self.manager_user.groups.set([self.manager_role.group])
        self.child_user.groups.set([self.employee_role.group])
        self.grandchild_user.groups.set([self.employee_role.group])
        self.other_user.groups.set([self.employee_role.group])

        self.manager = Employee.objects.create(user=self.manager_user)
        self.child = Employee.objects.create(user=self.child_user, manager=self.manager)
        self.grandchild = Employee.objects.create(user=self.grandchild_user, manager=self.child)
        self.other = Employee.objects.create(user=self.other_user)

    def test_manager_sees_self_and_recursive_reports(self):
        visible_ids = set(Employee.objects.visible_to(self.manager_user).values_list("id", flat=True))

        self.assertEqual(visible_ids, {self.manager.id, self.child.id, self.grandchild.id})

    def test_recursive_visibility_uses_two_queries_regardless_of_depth(self):
        with CaptureQueriesContext(connection) as captured_queries:
            visible_ids = set(
                Employee.objects.visible_to(self.manager_user).values_list(
                    "id",
                    flat=True,
                )
            )

        application_queries = [
            query
            for query in captured_queries.captured_queries
            if not query["sql"].lstrip().upper().startswith("EXPLAIN")
        ]
        self.assertEqual(len(application_queries), 2)
        self.assertEqual(visible_ids, {self.manager.id, self.child.id, self.grandchild.id})

    def test_manager_can_not_see_unrelated_employee_through_api(self):
        self.client.force_authenticate(self.manager_user)

        response = self.client.get(reverse("accounts:employee-list"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        visible_ids = {item["id"] for item in response.data["results"]}
        self.assertEqual(visible_ids, {self.manager.id, self.child.id, self.grandchild.id})

    def test_simple_jwt_bearer_token_authenticates_api_request(self):
        access_token = RefreshToken.for_user(self.manager_user).access_token
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {access_token}")

        response = self.client.get(reverse("accounts:employee-list"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_employee_without_add_permission_can_not_create_employee(self):
        self.client.force_authenticate(self.child_user)

        response = self.client.post(
            reverse("accounts:employee-list"),
            {"user": self.other_user.pk},
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_management_cycle_is_rejected(self):
        self.manager.manager = self.grandchild

        with self.assertRaises(ValidationError):
            self.manager.save()
