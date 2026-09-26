from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

from django.db import connection, connections
from django.test import TransactionTestCase

from common.exceptions import InvalidStateTransition
from inventory.models import StockBalance, StockMovement
from invoices.models import Invoice, InvoiceItem
from invoices.services.lifecycle import ConfirmInvoice

from .helpers import InvoiceTestMixin


class InvoiceConcurrencyTests(InvoiceTestMixin, TransactionTestCase):
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

    def test_concurrent_invoice_confirmation_consumes_stock_once(self):
        if connection.vendor != "postgresql":
            self.skipTest("This test verifies PostgreSQL row-lock semantics.")

        invoice = Invoice.objects.create(
            customer=self.customer,
            site=self.site,
            created_by=self.user,
            status=Invoice.Status.DRAFT,
        )
        InvoiceItem.objects.create(
            invoice=invoice,
            product=self.product,
            quantity=1,
            unit_price=100,
        )
        StockBalance.objects.create(
            location=self.location,
            product=self.product,
            quantity=1,
        )

        results = self._run_concurrently(
            lambda: ConfirmInvoice()(invoice.pk, actor=None),
        )

        successes = [result for result in results if not isinstance(result, Exception)]
        failures = [result for result in results if isinstance(result, InvalidStateTransition)]

        self.assertEqual(len(successes), 1)
        self.assertEqual(len(failures), 1)
        self.assertEqual(
            StockBalance.objects.get(
                location=self.location,
                product=self.product,
            ).quantity,
            0,
        )
        self.assertEqual(
            StockMovement.objects.filter(
                movement_type=StockMovement.MovementType.SALE,
            ).count(),
            1,
        )

        invoice.refresh_from_db()
        self.assertEqual(invoice.status, Invoice.Status.CONFIRMED)
