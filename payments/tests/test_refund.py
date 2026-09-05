from decimal import Decimal

from django.test import TestCase

from common.exceptions import InvalidBusinessOperation
from payments.models import PaymentRefund
from payments.services import collect, refund_payment

from .helpers import PaymentTestMixin


class RefundServiceTests(PaymentTestMixin, TestCase):
    def setUp(self):
        super().setUp()
        self.invoice = self.create_invoice()
        self.tx = collect(
            customer=self.customer,
            cash_amount=Decimal("100"),
            transfer_amount=Decimal("0"),
            collected_by_id=self.user.pk,
            actor=self.user,
        )

    def test_partial_refund(self):
        invoice = refund_payment(
            transaction_id=self.tx.pk,
            invoice_id=self.invoice.pk,
            amount=Decimal("40"),
            created_by_id=self.user.pk,
            actor=self.user,
        )
        self.assertEqual(PaymentRefund.objects.count(), 1)
        self.assertEqual(invoice.paid_amount, Decimal("60.00"))
        self.assertEqual(invoice.status, invoice.Status.CONFIRMED)

    def test_refund_cannot_exceed_allocation(self):
        with self.assertRaisesMessage(InvalidBusinessOperation, "Refund amount exceeds refundable"):
            refund_payment(
                transaction_id=self.tx.pk,
                invoice_id=self.invoice.pk,
                amount=Decimal("101"),
                created_by_id=self.user.pk,
                actor=self.user,
            )

    def test_zero_refund_rejected(self):
        with self.assertRaises(InvalidBusinessOperation):
            refund_payment(
                transaction_id=self.tx.pk,
                invoice_id=self.invoice.pk,
                amount=Decimal("0"),
                created_by_id=self.user.pk,
                actor=self.user,
            )
