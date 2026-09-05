from django.test import TestCase

from inventory.models import StockLocation, StockMovement, StockMovementItem

from .helpers import InventoryTestMixin


class InventoryModelTests(InventoryTestMixin, TestCase):
    def test_vehicle_belongs_to_employee(self):
        self.assertEqual(self.vehicle.employee, self.user)
        self.assertEqual(self.vehicle.location_type, StockLocation.LocationType.SALES_VEHICLE)

    def test_stock_movement_can_record_multiple_items(self):
        movement = StockMovement.objects.create(
            movement_type=StockMovement.MovementType.PURCHASE,
            destination_location=self.warehouse,
            created_by=self.user,
        )
        StockMovementItem.objects.create(movement=movement, product=self.product, quantity=10)
        self.assertEqual(movement.items.count(), 1)
