from decimal import Decimal

from django.test import TransactionTestCase

from common.exceptions import InsufficientStock, InvalidBusinessOperation, InvalidStateTransition
from inventory.models import StockBalance, StockMovement
from invoices.models import Invoice, InvoiceItem
from invoices.services import CancelInvoice, ConfirmInvoice, CreateInvoice, InvoiceNotFound
from .helpers import InvoiceTestMixin


class InvoiceLifecycleTests(InvoiceTestMixin, TransactionTestCase):
    def create_invoice(self, *, status=Invoice.Status.DRAFT, quantity=1):
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

    def test_create_uses_server_product_price(self):
        invoice = CreateInvoice()(
            created_by_id=self.user.pk,
            validated_data={
                "customer": self.customer,
                "items": [{"product": self.product, "quantity": 2, "unit_price": Decimal("1.00")}],
            },
        )
        self.assertEqual(invoice.items.get().unit_price, Decimal("100.00"))

    def test_confirm_consumes_stock(self):
        invoice = self.create_invoice()
        StockBalance.objects.create(location=self.location, product=self.product, quantity=10)

        ConfirmInvoice()(invoice.pk)

        invoice.refresh_from_db()
        self.assertEqual(invoice.status, Invoice.Status.CONFIRMED)
        self.assertEqual(StockBalance.objects.get(location=self.location, product=self.product).quantity, 9)
        self.assertTrue(StockMovement.objects.filter(reference=f"Invoice #{invoice.pk}").exists())

    def test_confirm_rolls_back_when_stock_is_missing(self):
        invoice = self.create_invoice()
        StockBalance.objects.create(location=self.location, product=self.product, quantity=0)

        with self.assertRaises(InsufficientStock):
            ConfirmInvoice()(invoice.pk)

        invoice.refresh_from_db()
        self.assertEqual(invoice.status, Invoice.Status.DRAFT)
        self.assertFalse(StockMovement.objects.exists())

    def test_unknown_invoice_raises_domain_error(self):
        with self.assertRaises(InvoiceNotFound):
            ConfirmInvoice()(999999)

    def test_cancel_draft(self):
        invoice = self.create_invoice()
        CancelInvoice()(invoice.pk)
        invoice.refresh_from_db()
        self.assertEqual(invoice.status, Invoice.Status.CANCELLED)

    def test_cancel_confirmed_restores_stock(self):
        invoice = self.create_invoice()
        StockBalance.objects.create(location=self.location, product=self.product, quantity=10)
        ConfirmInvoice()(invoice.pk)

        CancelInvoice()(invoice.pk)

        self.assertEqual(StockBalance.objects.get(location=self.location, product=self.product).quantity, 10)
        invoice.refresh_from_db()
        self.assertEqual(invoice.status, Invoice.Status.CANCELLED)

    def test_cancel_confirmed_rejects_when_source_stock_has_moved(self):
        invoice = self.create_invoice()
        StockBalance.objects.create(location=self.location, product=self.product, quantity=10)
        ConfirmInvoice()(invoice.pk)

        StockBalance.objects.filter(location=self.location, product=self.product).update(quantity=0, total_cost=Decimal("0.00"))

        with self.assertRaises(InvalidBusinessOperation):
            CancelInvoice()(invoice.pk)

        invoice.refresh_from_db()
        self.assertEqual(invoice.status, Invoice.Status.CONFIRMED)
        self.assertEqual(StockMovement.objects.filter(reference=f"Cancel Invoice #{invoice.pk}").count(), 0)

    def test_cancel_rejects_partial_payment(self):
        invoice = self.create_invoice(status=Invoice.Status.CONFIRMED)
        from payments.models import PaymentAllocation, PaymentTransaction
        tx = PaymentTransaction.objects.create(
            customer=self.customer,
            collected_by=self.user,
            cash_amount=Decimal("10.00"),
            transfer_amount=Decimal("0.00"),
        )
        PaymentAllocation.objects.create(
            transaction=tx,
            invoice=invoice,
            cash_amount=Decimal("10.00"),
            transfer_amount=Decimal("0.00"),
        )

        with self.assertRaises(InvalidStateTransition):
            CancelInvoice()(invoice.pk)
