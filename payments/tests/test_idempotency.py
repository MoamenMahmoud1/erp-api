from decimal import Decimal

from django.db import IntegrityError
from django.test import TransactionTestCase

from payments.models import IdempotencyKey, PaymentAllocation, PaymentRefund, PaymentTransaction
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

    def test_zero_value_payment_records_are_rejected_at_database_boundary(self):
        with self.assertRaises(IntegrityError):
            PaymentTransaction.objects.create(
                customer=self.customer,
                collected_by=self.user,
                cash_amount=Decimal("0"),
                transfer_amount=Decimal("0"),
            )

        transaction = PaymentTransaction.objects.create(
            customer=self.customer,
            collected_by=self.user,
            cash_amount=Decimal("100"),
            transfer_amount=Decimal("0"),
        )
        invoice = self.create_invoice()
        with self.assertRaises(IntegrityError):
            PaymentAllocation.objects.create(
                transaction=transaction,
                invoice=invoice,
                cash_amount=Decimal("0"),
                transfer_amount=Decimal("0"),
            )
        allocation = PaymentAllocation.objects.create(
            transaction=transaction,
            invoice=invoice,
            cash_amount=Decimal("100"),
            transfer_amount=Decimal("0"),
        )
        with self.assertRaises(IntegrityError):
            PaymentRefund.objects.create(
                transaction=transaction,
                invoice=invoice,
                allocation=allocation,
                cash_amount=Decimal("0"),
                transfer_amount=Decimal("0"),
                created_by=self.user,
            )

    def test_idempotency_response_status_allows_pending_and_http_status_codes(self):
        pending = IdempotencyKey.objects.create(
            key="pending",
            user=self.user,
            path="/payments/collections/",
            request_signature="a" * 64,
            response_status=0,
            response_body={},
        )
        self.assertEqual(pending.response_status, 0)

        complete = IdempotencyKey.objects.create(
            key="complete",
            user=self.user,
            path="/payments/collections/",
            request_signature="b" * 64,
            response_status=201,
            response_body={"ok": True},
        )
        self.assertEqual(complete.response_status, 201)
