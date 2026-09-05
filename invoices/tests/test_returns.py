from decimal import Decimal

from django.test import TestCase

from inventory.models import StockBalance, StockMovement
from invoices.models import Invoice, InvoiceItem
from invoices.services import CreateSalesReturn, ConfirmInvoice
from payments.models import PaymentAllocation, PaymentTransaction

from .helpers import InvoiceTestMixin


class SalesReturnTests(InvoiceTestMixin, TestCase):
    def test_partial_paid_invoice_cannot_be_returned(self):
        invoice = Invoice.objects.create(
            customer=self.customer,
            created_by=self.user,
            status=Invoice.Status.CONFIRMED,
        )
        InvoiceItem.objects.create(invoice=invoice, product=self.product, quantity=1, unit_price=Decimal("100.00"))
        from common.exceptions import InvalidBusinessOperation

        with self.assertRaises(InvalidBusinessOperation):
            CreateSalesReturn()(
                invoice_id=invoice.pk,
                items=[{"invoice_item": invoice.items.get(), "quantity": 1}],
                created_by_id=self.user.pk,
                actor=self.user,
            )

    def test_paid_invoice_return_refunds_and_restores_stock(self):
        invoice = Invoice.objects.create(customer=self.customer, created_by=self.user, status=Invoice.Status.CONFIRMED)
        line = InvoiceItem.objects.create(invoice=invoice, product=self.product, quantity=2, unit_price=Decimal("100.00"))
        StockBalance.objects.create(location=self.location, product=self.product, quantity=2)
        ConfirmInvoice()(invoice.pk)

        tx = PaymentTransaction.objects.create(
            customer=self.customer,
            collected_by=self.user,
            cash_amount=Decimal("200.00"),
            transfer_amount=Decimal("0.00"),
        )
        PaymentAllocation.objects.create(
            transaction=tx,
            invoice=invoice,
            cash_amount=Decimal("200.00"),
            transfer_amount=Decimal("0.00"),
        )
        invoice.refresh_from_db()

        returned = CreateSalesReturn()(
            invoice_id=invoice.pk,
            items=[{"invoice_item": line, "quantity": 1}],
            created_by_id=self.user.pk,
            actor=self.user,
        )

        self.assertEqual(returned.total_amount, Decimal("100.00"))
        invoice.refresh_from_db()
        self.assertEqual(invoice.status, Invoice.Status.CONFIRMED)
        self.assertEqual(invoice.paid_amount, Decimal("100.00"))
        self.assertEqual(StockBalance.objects.get(location=self.location, product=self.product).quantity, 1)
        self.assertTrue(
            StockMovement.objects.filter(
                movement_type=StockMovement.MovementType.SALEABLE_RETURN,
                reference=f"Return Invoice #{invoice.pk}",
            ).exists()
        )

    def test_return_cannot_exceed_line_quantity(self):
        invoice = Invoice.objects.create(customer=self.customer, created_by=self.user, status=Invoice.Status.PAID)
        line = InvoiceItem.objects.create(invoice=invoice, product=self.product, quantity=1, unit_price=Decimal("100.00"))
        from common.exceptions import InvalidBusinessOperation

        with self.assertRaises(InvalidBusinessOperation):
            CreateSalesReturn()(
                invoice_id=invoice.pk,
                items=[{"invoice_item": line, "quantity": 2}],
                created_by_id=self.user.pk,
                actor=self.user,
            )
