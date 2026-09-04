import json

from asgiref.sync import sync_to_async
from django.contrib.auth import get_user_model
from django.test import TransactionTestCase
from django.test.client import AsyncRequestFactory
from django.urls import resolve, reverse
from rest_framework.test import force_authenticate

from customers.api.views import CustomerViewSet
from customers.models import Customer
from invoices.models import Invoice


class CustomerAsyncAPITests(TransactionTestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(
            username="customer-reader",
            email="customer-reader@example.com",
            password="test-password",
            is_staff=False,
        )
        self.staff = User.objects.create_user(
            username="customer-staff",
            email="customer-staff@example.com",
            password="test-password",
            is_staff=True,
        )
        self.customer = Customer.objects.create(name="Acme")
        self.factory = AsyncRequestFactory()

    async def test_router_uses_async_crud_actions(self):
        list_view = resolve(reverse("customers:customer-list")).func
        detail_view = resolve(
            reverse("customers:customer-detail", kwargs={"pk": self.customer.pk})
        ).func

        self.assertEqual(list_view.actions["get"], "alist")
        self.assertEqual(list_view.actions["post"], "acreate")
        self.assertEqual(detail_view.actions["get"], "aretrieve")
        self.assertEqual(detail_view.actions["put"], "aupdate")
        self.assertEqual(detail_view.actions["patch"], "partial_aupdate")
        self.assertEqual(detail_view.actions["delete"], "adestroy")

    async def test_authenticated_user_can_list_customers(self):
        request = self.factory.get(reverse("customers:customer-list"))
        force_authenticate(request, user=self.user)

        response = await resolve(reverse("customers:customer-list")).func(request)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 1)

    async def test_staff_can_create_update_and_delete_customer(self):
        list_path = reverse("customers:customer-list")
        request = self.factory.post(
            list_path,
            data=json.dumps({"name": "New Customer", "phone": "123"}),
            content_type="application/json",
        )
        force_authenticate(request, user=self.staff)
        response = await resolve(list_path).func(request)
        self.assertEqual(response.status_code, 201)
        customer_id = response.data["id"]

        detail_path = reverse(
            "customers:customer-detail",
            kwargs={"pk": customer_id},
        )
        request = self.factory.patch(
            detail_path,
            data=json.dumps({"name": "Updated Customer"}),
            content_type="application/json",
        )
        force_authenticate(request, user=self.staff)
        response = await resolve(detail_path).func(request, pk=customer_id)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["name"], "Updated Customer")

        request = self.factory.delete(detail_path)
        force_authenticate(request, user=self.staff)
        response = await resolve(detail_path).func(request, pk=customer_id)
        self.assertEqual(response.status_code, 204)
        self.assertFalse(await Customer.objects.filter(pk=customer_id).aexists())

    async def test_non_staff_cannot_write_customer(self):
        request = self.factory.post(
            reverse("customers:customer-list"),
            data=json.dumps({"name": "Blocked"}),
            content_type="application/json",
        )
        force_authenticate(request, user=self.user)

        response = await resolve(reverse("customers:customer-list")).func(request)

        self.assertEqual(response.status_code, 403)

    async def test_referenced_customer_cannot_be_deleted(self):
        await sync_to_async(
            Invoice.objects.create,
            thread_sensitive=True,
        )(
            customer=self.customer,
            created_by=self.staff,
        )
        path = reverse(
            "customers:customer-detail",
            kwargs={"pk": self.customer.pk},
        )
        request = self.factory.delete(path)
        force_authenticate(request, user=self.staff)

        response = await resolve(path).func(request, pk=self.customer.pk)

        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.data["code"], "customer_in_use")
        self.assertTrue(await Customer.objects.filter(pk=self.customer.pk).aexists())
