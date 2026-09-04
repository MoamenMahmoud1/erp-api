from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase

from products.models import Product

from .models import (
    StockBalance,
    StockLocation,
    StockMovement,
    StockMovementItem,
)
from .services.stock_balance import StockBalanceService
from .services.transfer_stock import TransferStockService


User = get_user_model()


class InventoryTestMixin:
    def create_user(self, username="stock-user"):
        return User.objects.create_user(
            username=username,
            email=f"{username}@example.com",
            password="test-password",
        )

    def create_product(
        self,
        name="Test Product",
        purchase_price="100.00",
        selling_price="150.00",
    ):
        return Product.objects.create(
            name=name,
            purchase_price=Decimal(purchase_price),
            selling_price=Decimal(selling_price),
        )

    def create_locations(self):
        warehouse = StockLocation.objects.create(
            name="Main Warehouse",
            location_type=StockLocation.LocationType.MAIN_WAREHOUSE,
        )

        vehicle = StockLocation.objects.create(
            name="Van 01",
            location_type=StockLocation.LocationType.SALES_VEHICLE,
            employee=self.user,
        )

        return warehouse, vehicle


class StockLocationTests(InventoryTestMixin, TestCase):
    def setUp(self):
        self.user = self.create_user()

    def test_create_main_warehouse(self):
        location = StockLocation.objects.create(
            name="Main Warehouse",
            location_type=StockLocation.LocationType.MAIN_WAREHOUSE,
        )

        self.assertEqual(
            location.location_type,
            StockLocation.LocationType.MAIN_WAREHOUSE,
        )
        self.assertTrue(location.is_active)

    def test_sales_vehicle_can_be_assigned_to_employee(self):
        location = StockLocation.objects.create(
            name="Van 01",
            location_type=StockLocation.LocationType.SALES_VEHICLE,
            employee=self.user,
        )

        self.assertEqual(location.employee, self.user)
        self.assertEqual(
            location.location_type,
            StockLocation.LocationType.SALES_VEHICLE,
        )


class StockMovementTests(InventoryTestMixin, TestCase):
    def setUp(self):
        self.user = self.create_user()
        self.warehouse, self.vehicle = self.create_locations()
        self.product = self.create_product()

    def test_transfer_movement(self):
        movement = StockMovement.objects.create(
            movement_type=StockMovement.MovementType.TRANSFER,
            source_location=self.warehouse,
            destination_location=self.vehicle,
            created_by=self.user,
            reference="TRANSFER-001",
        )

        item = StockMovementItem.objects.create(
            movement=movement,
            product=self.product,
            quantity=20,
        )

        self.assertEqual(
            movement.source_location,
            self.warehouse,
        )
        self.assertEqual(
            movement.destination_location,
            self.vehicle,
        )
        self.assertEqual(
            item.product,
            self.product,
        )
        self.assertEqual(
            item.quantity,
            20,
        )

    def test_movement_can_have_multiple_products(self):
        second_product = self.create_product(
            name="Second Product",
            purchase_price="50.00",
            selling_price="75.00",
        )

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

        StockMovementItem.objects.create(
            movement=movement,
            product=second_product,
            quantity=5,
        )

        self.assertEqual(
            movement.items.count(),
            2,
        )


class StockBalanceServiceTests(InventoryTestMixin, TestCase):
    def setUp(self):
        self.user = self.create_user()
        self.warehouse, self.vehicle = self.create_locations()
        self.product = self.create_product()

    def test_increase_creates_balance(self):
        balance = StockBalanceService.increase(
            location=self.warehouse,
            product=self.product,
            quantity=100,
        )

        self.assertEqual(
            balance.quantity,
            100,
        )

    def test_increase_adds_to_existing_balance(self):
        StockBalance.objects.create(
            location=self.warehouse,
            product=self.product,
            quantity=100,
        )

        balance = StockBalanceService.increase(
            location=self.warehouse,
            product=self.product,
            quantity=25,
        )

        self.assertEqual(
            balance.quantity,
            125,
        )

    def test_decrease_reduces_balance(self):
        StockBalance.objects.create(
            location=self.warehouse,
            product=self.product,
            quantity=100,
        )

        balance = StockBalanceService.decrease(
            location=self.warehouse,
            product=self.product,
            quantity=30,
        )

        self.assertEqual(
            balance.quantity,
            70,
        )

    def test_decrease_rejects_insufficient_stock(self):
        StockBalance.objects.create(
            location=self.warehouse,
            product=self.product,
            quantity=10,
        )

        with self.assertRaisesMessage(
            ValueError,
            "Insufficient stock.",
        ):
            StockBalanceService.decrease(
                location=self.warehouse,
                product=self.product,
                quantity=20,
            )

        balance = StockBalance.objects.get(
            location=self.warehouse,
            product=self.product,
        )

        self.assertEqual(
            balance.quantity,
            10,
        )

    def test_increase_rejects_zero_quantity(self):
        with self.assertRaisesMessage(
            ValueError,
            "Quantity must be greater than zero.",
        ):
            StockBalanceService.increase(
                location=self.warehouse,
                product=self.product,
                quantity=0,
            )

    def test_increase_rejects_negative_quantity(self):
        with self.assertRaisesMessage(
            ValueError,
            "Quantity must be greater than zero.",
        ):
            StockBalanceService.increase(
                location=self.warehouse,
                product=self.product,
                quantity=-1,
            )

    def test_decrease_rejects_zero_quantity(self):
        with self.assertRaisesMessage(
            ValueError,
            "Quantity must be greater than zero.",
        ):
            StockBalanceService.decrease(
                location=self.warehouse,
                product=self.product,
                quantity=0,
            )


class TransferStockServiceTests(InventoryTestMixin, TestCase):
    def setUp(self):
        self.user = self.create_user()
        self.warehouse, self.vehicle = self.create_locations()
        self.product = self.create_product()

        StockBalance.objects.create(
            location=self.warehouse,
            product=self.product,
            quantity=100,
        )

    def test_transfer_stock(self):
        movement = TransferStockService.execute(
            source=self.warehouse,
            destination=self.vehicle,
            items=[
                {
                    "product": self.product,
                    "quantity": 30,
                }
            ],
            created_by=self.user,
            reference="TRANSFER-001",
        )

        warehouse_balance = StockBalance.objects.get(
            location=self.warehouse,
            product=self.product,
        )

        vehicle_balance = StockBalance.objects.get(
            location=self.vehicle,
            product=self.product,
        )

        self.assertEqual(
            warehouse_balance.quantity,
            70,
        )
        self.assertEqual(
            vehicle_balance.quantity,
            30,
        )

        self.assertEqual(
            movement.movement_type,
            StockMovement.MovementType.TRANSFER,
        )

        self.assertEqual(
            movement.source_location,
            self.warehouse,
        )

        self.assertEqual(
            movement.destination_location,
            self.vehicle,
        )

        self.assertEqual(
            movement.items.count(),
            1,
        )

        item = movement.items.get()

        self.assertEqual(
            item.product,
            self.product,
        )

        self.assertEqual(
            item.quantity,
            30,
        )

    def test_transfer_rejects_insufficient_stock(self):
        with self.assertRaisesMessage(
            ValueError,
            "Insufficient stock.",
        ):
            TransferStockService.execute(
                source=self.warehouse,
                destination=self.vehicle,
                items=[
                    {
                        "product": self.product,
                        "quantity": 150,
                    }
                ],
                created_by=self.user,
            )

        warehouse_balance = StockBalance.objects.get(
            location=self.warehouse,
            product=self.product,
        )

        self.assertEqual(
            warehouse_balance.quantity,
            100,
        )

        self.assertFalse(
            StockMovement.objects.exists(),
        )

    def test_transfer_rejects_same_location(self):
        with self.assertRaisesMessage(
            ValueError,
            "Source and destination must be different.",
        ):
            TransferStockService.execute(
                source=self.warehouse,
                destination=self.warehouse,
                items=[
                    {
                        "product": self.product,
                        "quantity": 10,
                    }
                ],
                created_by=self.user,
            )

        self.assertFalse(
            StockMovement.objects.exists(),
        )

    def test_transfer_rejects_empty_items(self):
        with self.assertRaisesMessage(
            ValueError,
            "Transfer must contain at least one item.",
        ):
            TransferStockService.execute(
                source=self.warehouse,
                destination=self.vehicle,
                items=[],
                created_by=self.user,
            )

        self.assertFalse(
            StockMovement.objects.exists(),
        )

    def test_transfer_rejects_invalid_quantity(self):
        with self.assertRaisesMessage(
            ValueError,
            "Quantity must be greater than zero.",
        ):
            TransferStockService.execute(
                source=self.warehouse,
                destination=self.vehicle,
                items=[
                    {
                        "product": self.product,
                        "quantity": 0,
                    }
                ],
                created_by=self.user,
            )

        warehouse_balance = StockBalance.objects.get(
            location=self.warehouse,
            product=self.product,
        )

        self.assertEqual(
            warehouse_balance.quantity,
            100,
        )

        self.assertFalse(
            StockMovement.objects.exists(),
        )

    def test_transfer_multiple_products(self):
        second_product = self.create_product(
            name="Second Product",
            purchase_price="50.00",
            selling_price="75.00",
        )

        StockBalance.objects.create(
            location=self.warehouse,
            product=second_product,
            quantity=50,
        )

        movement = TransferStockService.execute(
            source=self.warehouse,
            destination=self.vehicle,
            items=[
                {
                    "product": self.product,
                    "quantity": 20,
                },
                {
                    "product": second_product,
                    "quantity": 15,
                },
            ],
            created_by=self.user,
        )

        self.assertEqual(
            movement.items.count(),
            2,
        )

        self.assertEqual(
            StockBalance.objects.get(
                location=self.warehouse,
                product=self.product,
            ).quantity,
            80,
        )

        self.assertEqual(
            StockBalance.objects.get(
                location=self.vehicle,
                product=self.product,
            ).quantity,
            20,
        )

        self.assertEqual(
            StockBalance.objects.get(
                location=self.warehouse,
                product=second_product,
            ).quantity,
            35,
        )

        self.assertEqual(
            StockBalance.objects.get(
                location=self.vehicle,
                product=second_product,
            ).quantity,
            15,
        )