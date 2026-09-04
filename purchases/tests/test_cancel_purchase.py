from django.contrib.auth import get_user_model
from django.test import TestCase

from products.models import Product
from purchases.models import Purchase, PurchaseItem
from purchases.services.cancel_purchase import CancelPurchaseService
from suppliers.models import Supplier


class CancelPurchaseServiceTests(TestCase):

    def setUp(self):
        User = get_user_model()

        self.user = User.objects.create_user(
            username="cancel_user",
            email="cancel@example.com",
            password="test-password",
        )

        self.supplier = Supplier.objects.create(
            name="Test Supplier",
        )

        self.product = Product.objects.create(
            name="Test Product",
            purchase_price=100,
            selling_price=150,
        )

        self.purchase = Purchase.objects.create(
            supplier=self.supplier,
            created_by=self.user,
            reference="PO-CANCEL-001",
        )

        PurchaseItem.objects.create(
            purchase=self.purchase,
            product=self.product,
            quantity=5,
            unit_purchase_price=100,
        )

    def test_cancel_purchase_updates_status(self):
        CancelPurchaseService.execute(
            purchase_id=self.purchase.id,
        )

        self.purchase.refresh_from_db()

        self.assertEqual(
            self.purchase.status,
            Purchase.Status.CANCELLED,
        )

    def test_cancel_purchase_cannot_cancel_confirmed_purchase(self):
        self.purchase.status = Purchase.Status.CONFIRMED
        self.purchase.save(update_fields=["status"])

        with self.assertRaisesMessage(
            ValueError,
            "Only draft purchases can be cancelled.",
        ):
            CancelPurchaseService.execute(
                purchase_id=self.purchase.id,
            )

        self.purchase.refresh_from_db()

        self.assertEqual(
            self.purchase.status,
            Purchase.Status.CONFIRMED,
        )

    def test_cancel_purchase_cannot_cancel_twice(self):
        CancelPurchaseService.execute(
            purchase_id=self.purchase.id,
        )

        with self.assertRaisesMessage(
            ValueError,
            "Only draft purchases can be cancelled.",
        ):
            CancelPurchaseService.execute(
                purchase_id=self.purchase.id,
            )

    def test_cancel_purchase_does_not_change_inventory(self):
        CancelPurchaseService.execute(
            purchase_id=self.purchase.id,
        )

        from inventory.models import StockBalance, StockMovement

        self.assertFalse(
            StockMovement.objects.exists(),
        )

        self.assertFalse(
            StockBalance.objects.exists(),
        )

    def test_cancel_purchase_not_found(self):
        with self.assertRaises(Purchase.DoesNotExist):
            CancelPurchaseService.execute(
                purchase_id=999999,
            )