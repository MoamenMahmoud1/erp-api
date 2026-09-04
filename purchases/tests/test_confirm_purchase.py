from decimal import Decimal
from unittest.mock import patch
from django.contrib.auth import get_user_model
from django.test import TestCase

from inventory.models import (
    StockBalance,
    StockLocation,
    StockMovement,
    StockMovementItem,
)

from products.models import Product
from purchases.models import Purchase, PurchaseItem
from purchases.services.confirm_purchase import ConfirmPurchaseService
from suppliers.models import Supplier


class ConfirmPurchaseServiceTests(TestCase):

    def setUp(self):
        User = get_user_model()

        self.user = User.objects.create_user(
            username="purchase_user",
            email="purchase@example.com",
            password="test-password",
        )

        self.supplier = Supplier.objects.create(
            name="Test Supplier",
        )

        self.product = Product.objects.create(
            name="Test Product",
            purchase_price=Decimal("100.00"),
            selling_price=Decimal("150.00"),
        )

        self.warehouse = StockLocation.objects.create(
            name="Main Warehouse",
            location_type=StockLocation.LocationType.MAIN_WAREHOUSE,
        )

        self.purchase = Purchase.objects.create(
            supplier=self.supplier,
            created_by=self.user,
            reference="PO-001",
        )

        PurchaseItem.objects.create(
            purchase=self.purchase,
            product=self.product,
            quantity=5,
            unit_purchase_price=Decimal("100.00"),
        )

    def test_confirm_purchase_updates_purchase_status(self):
        ConfirmPurchaseService.execute(
            purchase_id=self.purchase.id,
            created_by=self.user,
        )

        self.purchase.refresh_from_db()

        self.assertEqual(
            self.purchase.status,
            Purchase.Status.CONFIRMED,
        )

    def test_confirm_purchase_creates_stock_movement(self):
        ConfirmPurchaseService.execute(
            purchase_id=self.purchase.id,
            created_by=self.user,
        )

        movement = StockMovement.objects.get(
            reference=self.purchase.reference,
        )

        self.assertEqual(
            movement.movement_type,
            StockMovement.MovementType.PURCHASE,
        )

        self.assertEqual(
            movement.destination_location,
            self.warehouse,
        )

        self.assertEqual(
            movement.created_by,
            self.user,
        )

    def test_confirm_purchase_creates_movement_item(self):
        ConfirmPurchaseService.execute(
            purchase_id=self.purchase.id,
            created_by=self.user,
        )

        movement = StockMovement.objects.get(
            reference=self.purchase.reference,
        )

        movement_item = StockMovementItem.objects.get(
            movement=movement,
        )

        self.assertEqual(
            movement_item.product,
            self.product,
        )

        self.assertEqual(
            movement_item.quantity,
            5,
        )

    def test_confirm_purchase_increases_stock_balance(self):
        ConfirmPurchaseService.execute(
            purchase_id=self.purchase.id,
            created_by=self.user,
        )

        balance = StockBalance.objects.get(
            location=self.warehouse,
            product=self.product,
        )

        self.assertEqual(
            balance.quantity,
            5,
        )

    def test_confirm_purchase_cannot_be_confirmed_twice(self):
        ConfirmPurchaseService.execute(
            purchase_id=self.purchase.id,
            created_by=self.user,
        )

        with self.assertRaisesMessage(
            ValueError,
            "Only draft purchases can be confirmed.",
        ):
            ConfirmPurchaseService.execute(
                purchase_id=self.purchase.id,
                created_by=self.user,
            )

    def test_confirm_purchase_requires_items(self):
        purchase = Purchase.objects.create(
            supplier=self.supplier,
            created_by=self.user,
            reference="PO-002",
        )

        with self.assertRaisesMessage(
            ValueError,
            "Purchase must contain at least one item.",
        ):
            ConfirmPurchaseService.execute(
                purchase_id=purchase.id,
                created_by=self.user,
            )

        purchase.refresh_from_db()

        self.assertEqual(
            purchase.status,
            Purchase.Status.DRAFT,
        )

    def test_confirm_purchase_requires_active_main_warehouse(self):
        self.warehouse.is_active = False
        self.warehouse.save(update_fields=["is_active"])

        with self.assertRaisesMessage(
            ValueError,
            "Active main warehouse does not exist.",
        ):
            ConfirmPurchaseService.execute(
                purchase_id=self.purchase.id,
                created_by=self.user,
            )

        self.purchase.refresh_from_db()

        self.assertEqual(
            self.purchase.status,
            Purchase.Status.DRAFT,
        )

        self.assertFalse(
            StockMovement.objects.exists(),
        )
    

    @patch(
        "purchases.services.confirm_purchase.StockBalanceService.increase",
        side_effect=ValueError("Stock update failed."),
    )
    def test_confirm_purchase_rolls_back_on_stock_failure(
        self,
        mock_increase,
    ):
        with self.assertRaisesMessage(
            ValueError,
            "Stock update failed.",
        ):
            ConfirmPurchaseService.execute(
                purchase_id=self.purchase.id,
                created_by=self.user,
            )

        self.purchase.refresh_from_db()

        self.assertEqual(
            self.purchase.status,
            Purchase.Status.DRAFT,
        )

        self.assertFalse(
            StockMovement.objects.exists(),
        )

        self.assertFalse(
            StockMovementItem.objects.exists(),
        )

        self.assertFalse(
            StockBalance.objects.exists(),
        )