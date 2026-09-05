from decimal import Decimal

from django.test import TransactionTestCase

from invoices.models import Invoice
from payments.models import PaymentAllocation, PaymentTransaction
from payments.services import NoConfirmableInvoicesError, OverpaymentError, collect

from .helpers import PaymentTestMixin


class CollectionServiceTests(PaymentTestMixin, TransactionTestCase):
    def test_full_payment_marks_invoice_paid(self):
        invoice = self.create_invoice()
        tx = collect(
            customer=self.customer,
            cash_amount=Decimal("100"),
            transfer_amount=Decimal("0"),
            collected_by_id=self.user.pk,
            actor=self.user,
        )
        invoice.refresh_from_db()
        self.assertEqual(tx.total_amount, Decimal("100.00"))
        self.assertEqual(invoice.status, Invoice.Status.PAID)
        self.assertEqual(
            PaymentAllocation.objects.get(invoice=invoice).total_amount,
            Decimal("100.00"),
        )

    def test_partial_payment(self):
        invoice = self.create_invoice()
        collect(
            customer=self.customer,
            cash_amount=Decimal("30"),
            transfer_amount=Decimal("0"),
            collected_by_id=self.user.pk,
            actor=self.user,
        )
        invoice.refresh_from_db()
        self.assertEqual(invoice.status, Invoice.Status.CONFIRMED)
        self.assertEqual(invoice.outstanding_amount, Decimal("70.00"))

    def test_oldest_invoice_first(self):
        old = self.create_invoice(total="100.00")
        new = self.create_invoice(total="50.00")
        tx = collect(
            customer=self.customer,
            cash_amount=Decimal("120"),
            transfer_amount=Decimal("0"),
            collected_by_id=self.user.pk,
            actor=self.user,
        )
        self.assertEqual(
            PaymentAllocation.objects.get(transaction=tx, invoice=old).total_amount,
            Decimal("100.00"),
        )
        self.assertEqual(
            PaymentAllocation.objects.get(transaction=tx, invoice=new).total_amount,
            Decimal("20.00"),
        )

    def test_overpayment_rolls_back(self):
        self.create_invoice()
        with self.assertRaises(OverpaymentError):
            collect(
                customer=self.customer,
                cash_amount=Decimal("101"),
                transfer_amount=Decimal("0"),
                collected_by_id=self.user.pk,
                actor=self.user,
            )
        self.assertFalse(PaymentTransaction.objects.exists())

    def test_no_confirmed_invoice(self):
        self.create_invoice(status=Invoice.Status.DRAFT)
        with self.assertRaises(NoConfirmableInvoicesError):
            collect(
                customer=self.customer,
                cash_amount=Decimal("10"),
                transfer_amount=Decimal("0"),
                collected_by_id=self.user.pk,
                actor=self.user,
            )
