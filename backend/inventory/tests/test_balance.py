from django.test import TestCase

from inventory.models import StockBalance
from inventory.services.stock_balance import StockBalanceService

from .helpers import InventoryTestMixin


class StockBalanceServiceTests(InventoryTestMixin, TestCase):
    def test_increase_creates_balance(self):
        balance = StockBalanceService.increase(
            location=self.warehouse,
            product=self.product,
            quantity=100,
        )
        self.assertEqual(balance.quantity, 100)

    def test_increase_adds_to_existing_balance(self):
        StockBalance.objects.create(location=self.warehouse, product=self.product, quantity=100)
        balance = StockBalanceService.increase(
            location=self.warehouse,
            product=self.product,
            quantity=25,
        )
        self.assertEqual(balance.quantity, 125)

    def test_decrease_reduces_balance(self):
        StockBalance.objects.create(location=self.warehouse, product=self.product, quantity=100)
        balance = StockBalanceService.decrease(
            location=self.warehouse,
            product=self.product,
            quantity=30,
        )
        self.assertEqual(balance.quantity, 70)

    def test_decrease_rejects_insufficient_stock(self):
        StockBalance.objects.create(location=self.warehouse, product=self.product, quantity=10)
        with self.assertRaisesMessage(ValueError, "Insufficient stock."):
            StockBalanceService.decrease(
                location=self.warehouse,
                product=self.product,
                quantity=20,
            )
        self.assertEqual(
            StockBalance.objects.get(location=self.warehouse, product=self.product).quantity,
            10,
        )

    def test_invalid_quantities_are_rejected(self):
        for operation in (StockBalanceService.increase, StockBalanceService.decrease):
            with self.subTest(operation=operation.__name__):
                with self.assertRaisesMessage(ValueError, "Quantity must be greater than zero."):
                    operation(location=self.warehouse, product=self.product, quantity=0)
