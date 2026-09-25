from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

from django.db import connection, connections
from django.test import TransactionTestCase

from inventory.models import StockBalance
from inventory.services.stock_balance import StockBalanceService

from .helpers import InventoryTestMixin


class InventoryConcurrencyTests(InventoryTestMixin, TransactionTestCase):
    def _run_concurrently(self, operation, workers):
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

    def test_concurrent_decrements_never_oversell_stock(self):
        if connection.vendor != "postgresql":
            self.skipTest("This test verifies PostgreSQL row-lock semantics.")

        StockBalance.objects.create(
            location=self.warehouse,
            product=self.product,
            quantity=10,
        )

        results = self._run_concurrently(
            lambda: StockBalanceService.decrease(
                location=self.warehouse,
                product=self.product,
                quantity=1,
            ),
            workers=20,
        )

        successes = [result for result in results if not isinstance(result, Exception)]
        failures = [result for result in results if isinstance(result, Exception)]

        self.assertEqual(len(successes), 10)
        self.assertEqual(len(failures), 10)
        self.assertEqual(
            StockBalance.objects.get(
                location=self.warehouse,
                product=self.product,
            ).quantity,
            0,
        )
