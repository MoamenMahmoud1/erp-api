from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

from django.db import connection, connections
from django.test import TransactionTestCase

from payments.models import PaymentTransaction
from payments.services import process_idempotent

from .helpers import PaymentTestMixin


class IdempotencyConcurrencyTests(PaymentTestMixin, TransactionTestCase):
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

    def test_concurrent_same_idempotency_key_executes_business_operation_once(self):
        if connection.vendor != "postgresql":
            self.skipTest("This test verifies PostgreSQL transaction/lock semantics.")

        invoice = self.create_invoice(total="100.00")
        request_data = {
            "customer": self.customer.pk,
            "invoice": invoice.pk,
            "cash_amount": "100.00",
            "transfer_amount": "0.00",
        }

        results = self._run_concurrently(
            lambda: process_idempotent(
                key="concurrent-payment-key",
                user_id=self.user.pk,
                path="/api/v1/payments/collections/",
                data=request_data,
                customer=self.customer,
                invoice_id=invoice.pk,
                cash_amount=100,
                transfer_amount=0,
                actor=self.user,
            ),
        )

        self.assertTrue(all(not isinstance(result, Exception) for result in results))
        self.assertEqual(results[0].response_body, results[1].response_body)
        self.assertEqual(PaymentTransaction.objects.filter(customer=self.customer).count(), 1)

        invoice.refresh_from_db()
        self.assertEqual(invoice.status, "paid")
        self.assertEqual(invoice.outstanding_amount, 0)
