from django.test import TestCase

from common.exceptions import InvalidBusinessOperation
from inventory.models import StockBalance, StockMovement
from inventory.services.transfer_stock import TransferStock

from .helpers import InventoryTestMixin


class TransferServiceTests(InventoryTestMixin, TestCase):
    def setUp(self):
        super().setUp()
        StockBalance.objects.create(
            location=self.warehouse,
            product=self.product,
            quantity=100,
        )

    def transfer(self, quantity=30):
        return TransferStock()(
            source_id=self.warehouse.pk,
            destination_id=self.vehicle.pk,
            items=[{"product": self.product, "quantity": quantity}],
            created_by=self.user,
        )

    def test_transfer_moves_stock_and_records_ledger(self):
        movement = self.transfer()
        self.assertEqual(
            StockBalance.objects.get(location=self.warehouse, product=self.product).quantity,
            70,
        )
        self.assertEqual(
            StockBalance.objects.get(location=self.vehicle, product=self.product).quantity,
            30,
        )
        self.assertEqual(movement.movement_type, StockMovement.MovementType.TRANSFER)
        self.assertEqual(movement.items.count(), 1)

    def test_transfer_rolls_back_when_stock_is_insufficient(self):
        with self.assertRaises(ValueError):
            self.transfer(101)
        self.assertEqual(
            StockBalance.objects.get(location=self.warehouse, product=self.product).quantity,
            100,
        )
        self.assertFalse(StockMovement.objects.exists())

    def test_same_location_is_rejected(self):
        with self.assertRaises(InvalidBusinessOperation):
            TransferStock()(
                source_id=self.warehouse.pk,
                destination_id=self.warehouse.pk,
                items=[{"product": self.product, "quantity": 1}],
                created_by=self.user,
            )

    def test_duplicate_products_are_rejected(self):
        with self.assertRaises(InvalidBusinessOperation):
            TransferStock()(
                source_id=self.warehouse.pk,
                destination_id=self.vehicle.pk,
                items=[
                    {"product": self.product, "quantity": 1},
                    {"product": self.product, "quantity": 1},
                ],
                created_by=self.user,
            )
