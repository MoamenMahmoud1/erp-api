from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase, TransactionTestCase
from rest_framework.test import APIRequestFactory, force_authenticate

from customers.models import Customer
from inventory.models import StockBalance, StockLocation, StockMovement
from invoices.api.views import InvoiceViewSet
from invoices.models import Invoice, InvoiceItem
from invoices.services import CancelInvoice, ConfirmInvoice, CreateInvoice, InvoiceNotFound
from products.models import Product


class InvoiceTestMixin:
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(
            username="invoice-user",
            email="invoice@example.com",
            password="StrongPass123!",
            is_staff=True,
        )
        self.customer = Customer.objects.create(name="Acme")
        self.product = Product.objects.create(
            name="Widget",
            purchase_price=Decimal("50.00"),
            selling_price=Decimal("100.00"),
        )
        self.location = StockLocation.objects.create(
            name="Van 01",
            location_type=StockLocation.LocationType.SALES_VEHICLE,
            employee=self.user,
        )

    def create_invoice(self, status=Invoice.Status.DRAFT, quantity=1):
        invoice = Invoice.objects.create(
            customer=self.customer,
            created_by=self.user,
            status=status,
        )
        InvoiceItem.objects.create(
            invoice=invoice,
            product=self.product,
            quantity=quantity,
            unit_price=Decimal("100.00"),
        )
        return invoice


class InvoiceServiceTests(InvoiceTestMixin, TransactionTestCase):
    def test_create_invoice_uses_server_product_price(self):
        invoice = CreateInvoice()(
            created_by_id=self.user.pk,
            validated_data={
                "customer": self.customer,
                "items": [
                    {"product": self.product, "quantity": 2, "unit_price": Decimal("1.00")}
                ],
            },
        )
        item = invoice.items.get()
        self.assertEqual(item.unit_price, Decimal("100.00"))
        self.assertEqual(item.quantity, 2)

    def test_confirm_invoice_consumes_stock_and_creates_sale(self):
        invoice = self.create_invoice()
        StockBalance.objects.create(
            location=self.location,
            product=self.product,
            quantity=10,
        )

        ConfirmInvoice()(invoice.pk)

        invoice.refresh_from_db()
        balance = StockBalance.objects.get(location=self.location, product=self.product)
        self.assertEqual(invoice.status, Invoice.Status.CONFIRMED)
        self.assertEqual(balance.quantity, 9)
        self.assertTrue(
            StockMovement.objects.filter(
                reference=f"Invoice #{invoice.pk}",
                movement_type=StockMovement.MovementType.SALE,
            ).exists()
        )

    def test_confirm_requires_sufficient_stock(self):
        invoice = self.create_invoice()
        StockBalance.objects.create(
            location=self.location,
            product=self.product,
            quantity=0,
        )

        with self.assertRaisesMessage(Exception, "Insufficient stock"):
            ConfirmInvoice()(invoice.pk)

        invoice.refresh_from_db()
        self.assertEqual(invoice.status, Invoice.Status.DRAFT)
        self.assertFalse(StockMovement.objects.exists())

    def test_confirm_unknown_invoice(self):
        with self.assertRaises(InvoiceNotFound):
            ConfirmInvoice()(999999)

    def test_cancel_draft_invoice(self):
        invoice = self.create_invoice()
        CancelInvoice()(invoice.pk)
        invoice.refresh_from_db()
        self.assertEqual(invoice.status, Invoice.Status.CANCELLED)

    def test_cancel_confirmed_invoice_restores_stock(self):
        invoice = self.create_invoice()
        StockBalance.objects.create(
            location=self.location,
            product=self.product,
            quantity=10,
        )
        ConfirmInvoice()(invoice.pk)
        CancelInvoice()(invoice.pk)

        invoice.refresh_from_db()
        balance = StockBalance.objects.get(location=self.location, product=self.product)
        self.assertEqual(invoice.status, Invoice.Status.CANCELLED)
        self.assertEqual(balance.quantity, 10)
        self.assertTrue(
            StockMovement.objects.filter(
                reference=f"Cancel Invoice #{invoice.pk}",
                movement_type=StockMovement.MovementType.SALEABLE_RETURN,
            ).exists()
        )


class InvoiceAPITests(InvoiceTestMixin, TestCase):
    def setUp(self):
        super().setUp()
        self.factory = APIRequestFactory()

    def test_confirm_endpoint_is_synchronous(self):
        invoice = self.create_invoice()
        StockBalance.objects.create(
            location=self.location,
            product=self.product,
            quantity=10,
        )
        request = self.factory.post(f"/api/v1/invoices/{invoice.pk}/confirm/")
        force_authenticate(request, user=self.user)
        response = InvoiceViewSet.as_view({"post": "confirm"})(request, pk=invoice.pk)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["status"], Invoice.Status.CONFIRMED)

    def test_cancel_endpoint(self):
        invoice = self.create_invoice()
        request = self.factory.post(f"/api/v1/invoices/{invoice.pk}/cancel/")
        force_authenticate(request, user=self.user)
        response = InvoiceViewSet.as_view({"post": "cancel"})(request, pk=invoice.pk)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["status"], Invoice.Status.CANCELLED)
