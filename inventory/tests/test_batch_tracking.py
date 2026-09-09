from datetime import date, timedelta
from decimal import Decimal

from django.test import TestCase
from django.utils import timezone

from inventory.models import InventoryBatch, StockBalance, StockBatchBalance, StockLocation, StockMovement, StockMovementItem
from inventory.services.stock_balance import StockBalanceService
from products.models import Product


class BatchTrackingTests(TestCase):
    def setUp(self):
        self.product = Product.objects.create(
            name="Perishable Product",
            purchase_price=Decimal("10.00"),
            selling_price=Decimal("15.00"),
        )
        self.location = StockLocation.objects.create(
            name="Batch Warehouse",
            location_type=StockLocation.LocationType.MAIN_WAREHOUSE,
        )
        today = timezone.localdate()
        self.expired = InventoryBatch.objects.create(
            product=self.product,
            batch_number="OLD",
            manufactured_date=today - timedelta(days=30),
            expiry_date=today - timedelta(days=1),
        )
        self.soon = InventoryBatch.objects.create(
            product=self.product,
            batch_number="SOON",
            manufactured_date=today - timedelta(days=5),
            expiry_date=today + timedelta(days=3),
        )
        self.later = InventoryBatch.objects.create(
            product=self.product,
            batch_number="LATER",
            manufactured_date=today,
            expiry_date=today + timedelta(days=20),
        )

    def test_fefo_uses_earliest_non_expired_batches_and_skips_expired(self):
        StockBalanceService.increase(location=self.location, product=self.product, quantity=2, unit_cost=Decimal("8"), batch=self.expired)
        StockBalanceService.increase(location=self.location, product=self.product, quantity=3, unit_cost=Decimal("10"), batch=self.soon)
        StockBalanceService.increase(location=self.location, product=self.product, quantity=4, unit_cost=Decimal("12"), batch=self.later)

        balance = StockBalanceService.decrease(location=self.location, product=self.product, quantity=5)
        allocations = balance._stock_allocations

        self.assertEqual([(row["batch"].batch_number, row["quantity"]) for row in allocations], [("SOON", 3), ("LATER", 2)])
        self.assertEqual(StockBatchBalance.objects.get(location=self.location, batch=self.expired).quantity, 2)
        self.assertEqual(StockBatchBalance.objects.get(location=self.location, batch=self.soon).quantity, 0)
        self.assertEqual(StockBatchBalance.objects.get(location=self.location, batch=self.later).quantity, 2)
        self.assertEqual(StockBalance.objects.get(location=self.location, product=self.product).quantity, 4)

    def test_expired_stock_is_not_issued(self):
        StockBalanceService.increase(location=self.location, product=self.product, quantity=2, unit_cost=Decimal("8"), batch=self.expired)
        with self.assertRaisesMessage(ValueError, "Insufficient non-expired stock."):
            StockBalanceService.decrease(location=self.location, product=self.product, quantity=1)

    def test_specific_batch_decrease_updates_aggregate_and_batch_balance(self):
        StockBalanceService.increase(location=self.location, product=self.product, quantity=5, unit_cost=Decimal("11"), batch=self.soon)
        unit_cost, removed_cost = StockBalanceService.decrease_specific_batch(location=self.location, batch=self.soon, quantity=2)
        self.assertEqual(unit_cost, Decimal("11.00"))
        self.assertEqual(removed_cost, Decimal("22.00"))
        self.assertEqual(StockBatchBalance.objects.get(location=self.location, batch=self.soon).quantity, 3)
        self.assertEqual(StockBalance.objects.get(location=self.location, product=self.product).quantity, 3)

    def test_movement_item_can_reference_batch(self):
        movement = StockMovement.objects.create(
            movement_type=StockMovement.MovementType.PURCHASE,
            destination_location=self.location,
            created_by_id=1,
        )
        item = StockMovementItem.objects.create(movement=movement, product=self.product, batch=self.soon, quantity=1, unit_cost=Decimal("10"))
        self.assertEqual(item.batch.batch_number, "SOON")
