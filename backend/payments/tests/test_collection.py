from decimal import Decimal

from django.test import TransactionTestCase

from accounting.models import JournalEntry
from invoices.models import Invoice
from payments.models import PaymentAllocation, PaymentTransaction
from payments.services import (
    NoConfirmableInvoicesError,
    OverpaymentError,
    approve_bank_transfer,
    collect,
)

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

    def test_targeted_payment_stays_on_selected_invoice(self):
        old = self.create_invoice(total="100.00")
        selected = self.create_invoice(total="50.00")
        tx = collect(
            customer=self.customer,
            cash_amount=Decimal("30"),
            transfer_amount=Decimal("0"),
            collected_by_id=self.user.pk,
            actor=self.user,
            invoice_id=selected.pk,
        )

        self.assertEqual(
            PaymentAllocation.objects.get(transaction=tx, invoice=selected).total_amount,
            Decimal("30.00"),
        )
        self.assertFalse(PaymentAllocation.objects.filter(transaction=tx, invoice=old).exists())

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

    
    def test_transfer_payment_stays_pending_until_approval(self):
        invoice = self.create_invoice(total="100.00")
        tx = collect(
            customer=self.customer,
            cash_amount=Decimal("0"),
            transfer_amount=Decimal("100"),
            collected_by_id=self.user.pk,
            actor=self.user,
        )
        invoice.refresh_from_db()
        tx.refresh_from_db()

        self.assertEqual(tx.transfer_status, "pending")
        self.assertEqual(tx.effective_total_amount, Decimal("0.00"))
        self.assertEqual(invoice.status, Invoice.Status.CONFIRMED)
        self.assertEqual(invoice.outstanding_amount, Decimal("100.00"))

    def test_approved_transfer_counts_as_paid(self):
        invoice = self.create_invoice(total="100.00")
        tx = collect(
            customer=self.customer,
            cash_amount=Decimal("0"),
            transfer_amount=Decimal("100"),
            collected_by_id=self.user.pk,
            actor=self.user,
        )

        approved = approve_bank_transfer(
            transaction_id=tx.pk,
            actor_id=self.user.pk,
            actor=self.user,
        )
        invoice.refresh_from_db()
        self.assertEqual(approved.transfer_status, "accepted")
        self.assertEqual(approved.effective_total_amount, Decimal("100.00"))
        self.assertEqual(invoice.status, Invoice.Status.PAID)
        self.assertEqual(invoice.outstanding_amount, Decimal("0.00"))
        self.assertTrue(
            JournalEntry.objects.filter(
                source_type="payment.transfer.approval",
                source_id=tx.pk,
                status=JournalEntry.Status.POSTED,
            ).exists()
        )
        self.assertFalse(
            JournalEntry.objects.filter(
                source_type="payment.collection",
                source_id=tx.pk,
                status=JournalEntry.Status.POSTED,
            ).exists()
        )

    def test_second_pending_transfer_cannot_be_approved_after_invoice_is_paid(self):
        invoice = self.create_invoice(total="100.00")
        first = collect(
            customer=self.customer,
            cash_amount=Decimal("0"),
            transfer_amount=Decimal("100"),
            collected_by_id=self.user.pk,
            actor=self.user,
        )
        second = collect(
            customer=self.customer,
            cash_amount=Decimal("0"),
            transfer_amount=Decimal("100"),
            collected_by_id=self.user.pk,
            actor=self.user,
        )

        approve_bank_transfer(
            transaction_id=first.pk,
            actor_id=self.user.pk,
            actor=self.user,
        )
        with self.assertRaisesMessage(Exception, "overpay"):
            approve_bank_transfer(
                transaction_id=second.pk,
                actor_id=self.user.pk,
                actor=self.user,
            )

        invoice.refresh_from_db()
        self.assertEqual(invoice.status, Invoice.Status.PAID)
        second.refresh_from_db()
        self.assertEqual(second.transfer_status, "pending")

    def test_mixed_collection_counts_only_cash_before_transfer_approval(self):
        invoice = self.create_invoice(total="100.00")
        tx = collect(
            customer=self.customer,
            cash_amount=Decimal("30"),
            transfer_amount=Decimal("70"),
            collected_by_id=self.user.pk,
            actor=self.user,
        )
        invoice.refresh_from_db()
        self.assertEqual(tx.effective_total_amount, Decimal("30.00"))
        self.assertEqual(invoice.outstanding_amount, Decimal("70.00"))
