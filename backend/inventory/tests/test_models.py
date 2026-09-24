from django.db import IntegrityError
from django.test import TestCase

from inventory.models import StockLocation, StockMovement, StockMovementItem

from .helpers import InventoryTestMixin


class InventoryModelTests(InventoryTestMixin, TestCase):
    def test_vehicle_belongs_to_employee(self):
        self.assertEqual(self.vehicle.employee, self.user)
        self.assertEqual(
            self.vehicle.location_type,
            StockLocation.LocationType.SALES_VEHICLE,
        )

    def test_stock_movement_can_record_multiple_items(self):
        movement = StockMovement.objects.create(
            movement_type=StockMovement.MovementType.PURCHASE,
            destination_location=self.warehouse,
            created_by=self.user,
        )
        StockMovementItem.objects.create(
            movement=movement,
            product=self.product,
            quantity=10,
        )
        self.assertEqual(movement.items.count(), 1)

    def test_movement_direction_must_match_type(self):
        with self.assertRaises(IntegrityError):
            StockMovement.objects.create(
                movement_type=StockMovement.MovementType.PURCHASE,
                source_location=self.warehouse,
                created_by=self.user,
            )

    def test_transfer_requires_two_distinct_locations(self):
        with self.assertRaises(IntegrityError):
            StockMovement.objects.create(
                movement_type=StockMovement.MovementType.TRANSFER,
                source_location=self.warehouse,
                destination_location=self.warehouse,
                created_by=self.user,
            )
