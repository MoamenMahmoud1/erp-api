from decimal import Decimal

from django.test import TestCase
from rest_framework.test import APIRequestFactory, force_authenticate

from inventory.models import StockBalance
from invoices.api.views import InvoiceViewSet
from invoices.models import Invoice

from .helpers import InvoiceTestMixin


class InvoiceAPITests(InvoiceTestMixin, TestCase):
    def setUp(self):
        super().setUp()
        self.factory = APIRequestFactory()

    def create_invoice(self):
        return Invoice.objects.create(customer=self.customer, created_by=self.user)

    def test_confirm_endpoint(self):
        invoice = self.create_invoice()
        from invoices.models import InvoiceItem
        InvoiceItem.objects.create(invoice=invoice, product=self.product, quantity=1, unit_price=Decimal("100.00"))
        StockBalance.objects.create(location=self.location, product=self.product, quantity=5)

        request = self.factory.post(f"/api/v1/invoices/{invoice.pk}/confirm/")
        force_authenticate(request, user=self.user)
        response = InvoiceViewSet.as_view({"post": "confirm"})(request, pk=invoice.pk)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["status"], Invoice.Status.CONFIRMED)

    def test_draft_patch_endpoint(self):
        invoice = self.create_invoice()
        request = self.factory.patch(
            f"/api/v1/invoices/{invoice.pk}/",
            {"customer": self.customer.pk},
            format="json",
        )
        force_authenticate(request, user=self.user)
        response = InvoiceViewSet.as_view({"patch": "partial_update"})(request, pk=invoice.pk)
        self.assertEqual(response.status_code, 200)

    def test_delete_draft_endpoint(self):
        invoice = self.create_invoice()
        request = self.factory.delete(f"/api/v1/invoices/{invoice.pk}/")
        force_authenticate(request, user=self.user)
        response = InvoiceViewSet.as_view({"delete": "destroy"})(request, pk=invoice.pk)
        self.assertEqual(response.status_code, 204)
