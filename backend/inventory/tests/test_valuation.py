from decimal import Decimal

from django.test import TestCase

from inventory.models import StockBalance, StockLocation
from inventory.services.stock_balance import StockBalanceService
from products.models import Product


class WeightedAverageValuationTests(TestCase):
    def setUp(self):
        self.product = Product.objects.create(name="Test Product", purchase_price=Decimal("10.00"), selling_price=Decimal("20.00"))
        self.location = StockLocation.objects.create(name="Main", location_type=StockLocation.LocationType.MAIN_WAREHOUSE, is_active=True)

    def test_weighted_average_cost_is_preserved_through_receipts_and_issues(self):
        StockBalanceService.increase(location=self.location, product=self.product, quantity=10, unit_cost=Decimal("10.00"))
        StockBalanceService.increase(location=self.location, product=self.product, quantity=10, unit_cost=Decimal("20.00"))
        balance = StockBalance.objects.get(location=self.location, product=self.product)
        self.assertEqual(balance.quantity, 20)
        self.assertEqual(balance.total_cost, Decimal("300.00"))
        self.assertEqual(balance.average_unit_cost, Decimal("15.00"))

        removed = StockBalanceService.decrease(location=self.location, product=self.product, quantity=10)
        balance.refresh_from_db()
        self.assertEqual(removed._removed_unit_cost, Decimal("15.00"))
        self.assertEqual(balance.quantity, 10)
        self.assertEqual(balance.total_cost, Decimal("150.00"))
