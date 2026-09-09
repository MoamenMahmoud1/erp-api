from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase

from common.exceptions import InvalidBusinessOperation
from inventory.models import StockBalance, StockLocation, StockMovement
from organization.models import Company
from products.models import Product
from purchases.models import Purchase, PurchaseItem
from purchases.services.confirm_purchase import ConfirmPurchaseService
from purchases.services.return_purchase import ReturnPurchase
from suppliers.models import Supplier


class PurchaseReturnTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(
            username="purchase-return",
            email="return@example.com",
            password="StrongPass123!",
            is_staff=True,
        )
        self.company = Company.objects.create(name="Purchase Return Test Company")
        self.supplier = Supplier.objects.create(name="Supplier")
        self.product = Product.objects.create(
            name="Product",
            purchase_price=Decimal("20.00"),
            selling_price=Decimal("30.00"),
        )
        self.warehouse = StockLocation.objects.create(
            name="Main",
            location_type=StockLocation.LocationType.MAIN_WAREHOUSE,
        )
        self.purchase = Purchase.objects.create(
            supplier=self.supplier,
            created_by=self.user,
            reference="PO-RET-1",
        )
        self.line = PurchaseItem.objects.create(
            purchase=self.purchase,
            product=self.product,
            quantity=5,
            unit_purchase_price=Decimal("20"),
        )
        ConfirmPurchaseService.execute(purchase_id=self.purchase.pk, actor=self.user)

    def test_partial_return_reduces_stock(self):
        result = ReturnPurchase()(
            purchase_id=self.purchase.pk,
            items=[{"purchase_item": self.line, "quantity": 2}],
            created_by_id=self.user.pk,
            actor=self.user,
            reason="Supplier rejected two units",
        )
        self.assertEqual(result.total_amount, Decimal("40.00"))
        self.assertEqual(
            StockBalance.objects.get(location=self.warehouse, product=self.product).quantity,
            3,
        )
        self.assertTrue(
            StockMovement.objects.filter(
                reference=f"Return Purchase #{self.purchase.pk}",
                movement_type=StockMovement.MovementType.PURCHASE_RETURN,
            ).exists()
        )

    def test_return_cannot_exceed_remaining_quantity(self):
        ReturnPurchase()(
            purchase_id=self.purchase.pk,
            items=[{"purchase_item": self.line, "quantity": 3}],
            created_by_id=self.user.pk,
            actor=self.user,
        )
        with self.assertRaises(InvalidBusinessOperation):
            ReturnPurchase()(
                purchase_id=self.purchase.pk,
                items=[{"purchase_item": self.line, "quantity": 3}],
                created_by_id=self.user.pk,
                actor=self.user,
            )

    def test_return_requires_confirmed_purchase(self):
        purchase = Purchase.objects.create(supplier=self.supplier, created_by=self.user)
        line = PurchaseItem.objects.create(
            purchase=purchase,
            product=self.product,
            quantity=1,
            unit_purchase_price=Decimal("20"),
        )
        with self.assertRaises(InvalidBusinessOperation):
            ReturnPurchase()(
                purchase_id=purchase.pk,
                items=[{"purchase_item": line, "quantity": 1}],
                created_by_id=self.user.pk,
                actor=self.user,
            )
