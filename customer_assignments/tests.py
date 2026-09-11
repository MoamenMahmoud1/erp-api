from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.test import TestCase
from rest_framework.test import APIRequestFactory, force_authenticate

from accounts.models import Employee, RoleProfile
from customers.api.views import CustomerViewSet
from customers.models import Customer

from .models import CustomerAssignment


class AssignedCustomerApiTests(TestCase):
    def test_shift_bound_user_only_receives_assigned_customers(self):
        User = get_user_model()
        group = Group.objects.create(name="Customer Assignment Rep")
        RoleProfile.objects.create(
            group=group,
            name="Customer Assignment Rep",
            level=10,
            scope=RoleProfile.Scope.SITE,
            requires_shift=True,
        )
        user = User.objects.create_user(
            username="assigned-customer-rep",
            password="StrongPass123!",
            is_staff=True,
        )
        user.groups.add(group)
        employee = Employee.objects.create(user=user)

        assigned = Customer.objects.create(name="Assigned Customer")
        unassigned = Customer.objects.create(name="Unassigned Customer")
        CustomerAssignment.objects.create(customer=assigned, employee=employee)

        request = APIRequestFactory().get("/api/v1/customers/")
        force_authenticate(request, user=user)
        response = CustomerViewSet.as_view({"get": "list"})(request)

        self.assertEqual(response.status_code, 200)
        self.assertEqual([item["id"] for item in response.data["results"]], [assigned.pk])
        self.assertNotIn(unassigned.pk, [item["id"] for item in response.data["results"]])
