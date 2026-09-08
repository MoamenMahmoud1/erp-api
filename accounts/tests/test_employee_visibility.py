import uuid

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from accounts.models import Employee
from authsession.http import ClientContext
from authsession.services import start_auth_session
from core.testing.roles import create_role

User = get_user_model()


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
        self.grandchild = Employee.objects.create(
            user=self.grandchild_user,
            manager=self.child,
        )
        self.other = Employee.objects.create(user=self.other_user)

    def test_manager_sees_self_and_recursive_reports(self):
        visible_ids = set(
            Employee.objects.visible_to(self.manager_user).values_list("id", flat=True)
        )
        self.assertEqual(visible_ids, {self.manager.id, self.child.id, self.grandchild.id})

    def test_recursive_visibility_uses_two_queries_regardless_of_depth(self):
        with CaptureQueriesContext(connection) as captured_queries:
            visible_ids = set(
                Employee.objects.visible_to(self.manager_user).values_list("id", flat=True)
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
        with self.captureOnCommitCallbacks(execute=True):
            session = start_auth_session(
                user=self.manager_user,
                client_context=ClientContext(
                    device_id=uuid.uuid4(),
                    device_name="test",
                    user_agent="test-agent",
                    ip_address="127.0.0.1",
                ),
            )
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {session.access_token}")

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
