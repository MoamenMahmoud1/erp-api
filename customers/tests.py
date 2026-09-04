from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from customers.models import Customer
from invoices.models import Invoice


class CustomerAPITests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(
            username="customer-reader",
            email="customer-reader@example.com",
            password="test-password",
        )
        self.staff = User.objects.create_user(
            username="customer-staff",
            email="customer-staff@example.com",
            password="test-password",
            is_staff=True,
        )
        self.customer = Customer.objects.create(name="Acme")
        self.client = APIClient()

    def test_authenticated_user_can_list_customers(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.get(reverse("customers:customer-list"))
        self.assertEqual(response.status_code, 200)

    def test_staff_can_create_update_and_delete_customer(self):
        self.client.force_authenticate(user=self.staff)
        response = self.client.post(
            reverse("customers:customer-list"),
            {"name": "New Customer", "phone": "123"},
            format="json",
        )
        self.assertEqual(response.status_code, 201)
        customer_id = response.data["id"]

        detail_url = reverse(
            "customers:customer-detail",
            kwargs={"pk": customer_id},
        )
        response = self.client.patch(
            detail_url,
            {"name": "Updated Customer"},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["name"], "Updated Customer")

        response = self.client.delete(detail_url)
        self.assertEqual(response.status_code, 204)
        self.assertFalse(Customer.objects.filter(pk=customer_id).exists())

    def test_non_staff_cannot_write_customer(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.post(
            reverse("customers:customer-list"),
            {"name": "Blocked"},
            format="json",
        )
        self.assertEqual(response.status_code, 403)

    def test_referenced_customer_cannot_be_deleted(self):
        Invoice.objects.create(
            customer=self.customer,
            created_by=self.staff,
        )
        self.client.force_authenticate(user=self.staff)
        response = self.client.delete(
            reverse(
                "customers:customer-detail",
                kwargs={"pk": self.customer.pk},
            )
        )
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.data["code"], "customer_in_use")
        self.assertTrue(Customer.objects.filter(pk=self.customer.pk).exists())
