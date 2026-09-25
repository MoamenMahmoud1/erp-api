from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

from django.db import connection, connections
from django.test import TransactionTestCase

from invoices.models import Invoice
from payments.models import PaymentAllocation, PaymentTransaction, PaymentRefund
from payments.services.collection import NoConfirmableInvoicesError, collect
from payments.services.refund import RefundAmountTooLarge, refund_payment

from .helpers import PaymentTestMixin


class PaymentConcurrencyTests(PaymentTestMixin, TransactionTestCase):
    def _run_concurrently(self, operation, workers=2):
        barrier = Barrier(workers)

        def runner():
            connections.close_all()
            try:
                barrier.wait(timeout=10)
                return operation()
            except Exception as exc:
                return exc
            finally:
                connections.close_all()

        with ThreadPoolExecutor(max_workers=workers) as executor:
            return list(executor.map(lambda _: runner(), range(workers)))

    def _collect_full_amount(self, invoice):
        return collect(
            customer=self.customer,
            cash_amount=invoice.total,
            transfer_amount=0,
            collected_by_id=self.user.pk,
            actor=self.user,
            invoice_id=invoice.pk,
        )

    def test_concurrent_collections_cannot_double_pay_invoice(self):
        if connection.vendor != "postgresql":
            self.skipTest("This test verifies PostgreSQL row-lock semantics.")

        invoice = self.create_invoice(total="100.00")

        results = self._run_concurrently(
            lambda: self._collect_full_amount(invoice),
        )

        successes = [result for result in results if not isinstance(result, Exception)]
        failures = [result for result in results if isinstance(result, NoConfirmableInvoicesError)]

        self.assertEqual(len(successes), 1)
        self.assertEqual(len(failures), 1)
        self.assertEqual(PaymentTransaction.objects.count(), 1)
        self.assertEqual(PaymentAllocation.objects.filter(invoice=invoice).count(), 1)

        invoice.refresh_from_db()
        self.assertEqual(invoice.status, Invoice.Status.PAID)
        self.assertEqual(invoice.outstanding_amount, 0)

    def test_concurrent_refunds_cannot_refund_same_allocation_twice(self):
        if connection.vendor != "postgresql":
            self.skipTest("This test verifies PostgreSQL row-lock semantics.")

        invoice = self.create_invoice(total="100.00")
        payment = collect(
            customer=self.customer,
            cash_amount=100,
            transfer_amount=0,
            collected_by_id=self.user.pk,
            actor=self.user,
            invoice_id=invoice.pk,
        )

        results = self._run_concurrently(
            lambda: refund_payment(
                transaction_id=payment.pk,
                invoice_id=invoice.pk,
                amount=100,
                created_by_id=self.user.pk,
                actor=self.user,
            ),
        )

        successes = [result for result in results if not isinstance(result, Exception)]
        failures = [result for result in results if isinstance(result, RefundAmountTooLarge)]

        self.assertEqual(len(successes), 1)
        self.assertEqual(len(failures), 1)
        self.assertEqual(PaymentRefund.objects.filter(invoice=invoice).count(), 1)

        invoice.refresh_from_db()
        self.assertEqual(invoice.net_paid_amount, 0)
        self.assertEqual(invoice.status, Invoice.Status.CONFIRMED)
