from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from accounts.models import Employee
from core.testing.roles import create_role

User = get_user_model()


class EmployeeFilterTests(TestCase):
    def setUp(self):
        role = create_role(
            code="filter-manager",
            level=40,
            permissions=("view_employee",),
        )
        other_role = create_role(
            code="filter-employee",
            level=10,
            permissions=("view_employee",),
        )

        self.manager_user = User.objects.create_user(
            username="filter-manager",
            email="manager@test.com",
        )
        self.target_user = User.objects.create_user(
            username="target-user",
            email="target@test.com",
            first_name="Target",
            last_name="Employee",
        )
        self.other_user = User.objects.create_user(
            username="other-user",
            email="other@test.com",
        )
        self.manager_user.groups.set([role.group])
        self.target_user.groups.set([other_role.group])
        self.other_user.groups.set([other_role.group])

        self.manager = Employee.objects.create(user=self.manager_user)
        self.target = Employee.objects.create(user=self.target_user, manager=self.manager)
        Employee.objects.create(user=self.other_user)

        self.client = APIClient()
        self.client.force_authenticate(self.manager_user)

    def test_employee_filter_keeps_a_visible_employee(self):
        response = self.client.get(
            reverse("accounts:employee-list"),
            {"employee": "target-user"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual([row["id"] for row in response.data["results"]], [self.target.pk])

    def test_manager_filter_means_reports_of_manager(self):
        response = self.client.get(
            reverse("accounts:employee-list"),
            {"manager": str(self.manager.pk)},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual([row["id"] for row in response.data["results"]], [self.target.pk])
