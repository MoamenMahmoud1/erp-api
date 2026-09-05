from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase

from inventory.models import StockBalance, StockLocation, StockMovement, StockMovementItem
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
            password="StrongPass123!",
            is_staff=True,
        )
        self.supplier = Supplier.objects.create(name="Test Supplier")
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

    def confirm(self):
        return ConfirmPurchaseService.execute(purchase_id=self.purchase.pk, actor=self.user)

    def test_confirm_updates_status_and_stock(self):
        self.confirm()
        self.purchase.refresh_from_db()
        self.assertEqual(self.purchase.status, Purchase.Status.CONFIRMED)
        self.assertEqual(
            StockBalance.objects.get(location=self.warehouse, product=self.product).quantity,
            5,
        )

    def test_confirm_records_movement_and_items(self):
        self.confirm()
        movement = StockMovement.objects.get(reference=self.purchase.reference)
        self.assertEqual(movement.movement_type, StockMovement.MovementType.PURCHASE)
        item = StockMovementItem.objects.get(movement=movement)
        self.assertEqual(item.product, self.product)
        self.assertEqual(item.quantity, 5)

    def test_confirm_cannot_be_repeated(self):
        self.confirm()
        from common.exceptions import InvalidStateTransition

        with self.assertRaises(InvalidStateTransition):
            self.confirm()
