from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase

from common.exceptions import InvalidBusinessOperation, InvalidStateTransition
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
            password="StrongPass123!",
            is_staff=True,
        )
        self.supplier = Supplier.objects.create(name="Test Supplier")
        self.product = Product.objects.create(
            name="Test Product",
            purchase_price=Decimal("100"),
            selling_price=Decimal("150"),
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
            unit_purchase_price=Decimal("100"),
        )

    def cancel(self):
        return CancelPurchaseService.execute(purchase_id=self.purchase.pk, actor=self.user)

    def test_cancel_draft(self):
        self.cancel()
        self.purchase.refresh_from_db()
        self.assertEqual(self.purchase.status, Purchase.Status.CANCELLED)

    def test_cancel_non_draft_rejected(self):
        self.purchase.status = Purchase.Status.CONFIRMED
        self.purchase.save(update_fields=("status",))
        with self.assertRaises(InvalidStateTransition):
            self.cancel()

    def test_cancel_is_not_repeatable(self):
        self.cancel()
        with self.assertRaises(InvalidStateTransition):
            self.cancel()

    def test_missing_purchase_is_a_business_error(self):
        with self.assertRaises(InvalidBusinessOperation):
            CancelPurchaseService.execute(purchase_id=999999, actor=self.user)
