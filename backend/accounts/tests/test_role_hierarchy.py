from django.contrib.auth import get_user_model
from django.test import TestCase

from accounts.models import RoleProfile
from core.testing.roles import create_role

User = get_user_model()


class RoleHierarchyTests(TestCase):
    def setUp(self):
        self.admin_role = create_role(level=80, code="admin")
        self.employee_role = create_role(level=10, code="employee")
        self.admin = User.objects.create_user(username="admin", email="admin@test.com")
        self.employee = User.objects.create_user(username="employee", email="employee@test.com")
        self.admin.groups.set([self.admin_role.group])
        self.employee.groups.set([self.employee_role.group])

    def test_higher_role_can_manage_lower_role(self):
        self.assertTrue(RoleProfile.can_manage_user(self.admin, self.employee))

    def test_lower_role_can_not_manage_higher_role(self):
        self.assertFalse(RoleProfile.can_manage_user(self.employee, self.admin))

    def test_new_user_does_not_receive_an_implicit_role(self):
        user = User.objects.create_user(username="new-user", email="new-user@test.com")
        self.assertFalse(user.groups.exists())

    def test_unauthenticated_actor_can_not_manage_users(self):
        self.assertFalse(RoleProfile.can_manage_user(None, self.employee))
