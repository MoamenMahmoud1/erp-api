from decimal import Decimal

from django.test import TransactionTestCase

from payments.models import PaymentTransaction
from payments.services import process_idempotent

from .helpers import PaymentTestMixin


class IdempotencyServiceTests(PaymentTestMixin, TransactionTestCase):
    def test_same_key_replays_response(self):
        self.create_invoice()
        data = {
            "customer": self.customer.pk,
            "cash_amount": "100.00",
            "transfer_amount": "0.00",
        }
        first = process_idempotent(
            key="same-key",
            user_id=self.user.pk,
            path="/api/v1/payments/collections/",
            data=data,
            customer=self.customer,
            cash_amount=Decimal("100"),
            transfer_amount=Decimal("0"),
            actor=self.user,
        )
        second = process_idempotent(
            key="same-key",
            user_id=self.user.pk,
            path="/api/v1/payments/collections/",
            data=data,
            customer=self.customer,
            cash_amount=Decimal("100"),
            transfer_amount=Decimal("0"),
            actor=self.user,
        )
        self.assertEqual(first.response_body, second.response_body)
        self.assertEqual(PaymentTransaction.objects.count(), 1)

    def test_same_key_with_different_body_conflicts(self):
        self.create_invoice()
        process_idempotent(
            key="same-key",
            user_id=self.user.pk,
            path="/api/v1/payments/collections/",
            data={"customer": self.customer.pk, "cash_amount": "20.00", "transfer_amount": "0.00"},
            customer=self.customer,
            cash_amount=Decimal("20"),
            transfer_amount=Decimal("0"),
            actor=self.user,
        )
        result = process_idempotent(
            key="same-key",
            user_id=self.user.pk,
            path="/api/v1/payments/collections/",
            data={"customer": self.customer.pk, "cash_amount": "30.00", "transfer_amount": "0.00"},
            customer=self.customer,
            cash_amount=Decimal("30"),
            transfer_amount=Decimal("0"),
            actor=self.user,
        )
        self.assertEqual(result, "mismatch")
