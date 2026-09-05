from decimal import Decimal

from django.test import TestCase

from common.exceptions import InvalidBusinessOperation
from inventory.models import StockBalance, StockMovement
from invoices.models import Invoice, InvoiceItem
from invoices.services import ConfirmInvoice, CreateSalesReturn
from payments.models import PaymentAllocation, PaymentTransaction

from .helpers import InvoiceTestMixin


class SalesReturnTests(InvoiceTestMixin, TestCase):
    def paid_invoice(self, quantity=2):
        invoice = Invoice.objects.create(
            customer=self.customer,
            created_by=self.user,
            status=Invoice.Status.CONFIRMED,
        )
        line = InvoiceItem.objects.create(
            invoice=invoice,
            product=self.product,
            quantity=quantity,
            unit_price=Decimal("100.00"),
        )
        StockBalance.objects.create(
            location=self.location,
            product=self.product,
            quantity=quantity,
        )
        ConfirmInvoice()(invoice.pk)
        tx = PaymentTransaction.objects.create(
            customer=self.customer,
            collected_by=self.user,
            cash_amount=Decimal("100.00") * quantity,
            transfer_amount=Decimal("0"),
        )
        PaymentAllocation.objects.create(
            transaction=tx,
            invoice=invoice,
            cash_amount=Decimal("100.00") * quantity,
            transfer_amount=Decimal("0"),
        )
        invoice.refresh_from_db()
        return invoice, line

    def test_return_requires_paid_invoice(self):
        invoice = Invoice.objects.create(
            customer=self.customer,
            created_by=self.user,
            status=Invoice.Status.CONFIRMED,
        )
        line = InvoiceItem.objects.create(
            invoice=invoice,
            product=self.product,
            quantity=1,
            unit_price=Decimal("100"),
        )
        with self.assertRaises(InvalidBusinessOperation):
            CreateSalesReturn()(
                invoice_id=invoice.pk,
                items=[{"invoice_item": line, "quantity": 1}],
                created_by_id=self.user.pk,
                actor=self.user,
            )

    def test_partial_return_refunds_and_restores_stock(self):
        invoice, line = self.paid_invoice()

        returned = CreateSalesReturn()(
            invoice_id=invoice.pk,
            items=[{"invoice_item": line, "quantity": 1}],
            created_by_id=self.user.pk,
            actor=self.user,
        )

        self.assertEqual(returned.total_amount, Decimal("100.00"))
        invoice.refresh_from_db()
        self.assertEqual(invoice.status, Invoice.Status.PAID)
        self.assertEqual(invoice.paid_amount, Decimal("200.00"))
        self.assertEqual(invoice.refunded_amount, Decimal("100.00"))
        self.assertEqual(invoice.outstanding_amount, Decimal("0.00"))
        self.assertEqual(StockBalance.objects.get(location=self.location, product=self.product).quantity, 1)

    def test_full_return_marks_invoice_returned(self):
        invoice, line = self.paid_invoice(quantity=1)

        returned = CreateSalesReturn()(
            invoice_id=invoice.pk,
            items=[{"invoice_item": line, "quantity": 1}],
            created_by_id=self.user.pk,
            actor=self.user,
        )

        invoice.refresh_from_db()
        self.assertEqual(invoice.status, Invoice.Status.RETURNED)
        self.assertEqual(returned.total_amount, Decimal("100.00"))
        self.assertEqual(invoice.outstanding_amount, Decimal("0.00"))

    def test_return_cannot_exceed_remaining_quantity(self):
        invoice, line = self.paid_invoice(quantity=1)
        CreateSalesReturn()(
            invoice_id=invoice.pk,
            items=[{"invoice_item": line, "quantity": 1}],
            created_by_id=self.user.pk,
            actor=self.user,
        )
        with self.assertRaises(InvalidBusinessOperation):
            CreateSalesReturn()(
                invoice_id=invoice.pk,
                items=[{"invoice_item": line, "quantity": 1}],
                created_by_id=self.user.pk,
                actor=self.user,
            )
