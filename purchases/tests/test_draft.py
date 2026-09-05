from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase

from common.exceptions import InvalidBusinessOperation
from products.models import Product
from purchases.models import Purchase, PurchaseItem
from purchases.services.draft import CreatePurchase, DeletePurchase, UpdatePurchase
from suppliers.models import Supplier


class PurchaseDraftServiceTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(
            username="draft-purchase",
            email="draft@example.com",
            password="StrongPass123!",
            is_staff=True,
        )
        self.supplier = Supplier.objects.create(name="Supplier")
        self.product = Product.objects.create(
            name="Product",
            purchase_price=Decimal("20.00"),
            selling_price=Decimal("30.00"),
        )
        self.purchase = CreatePurchase()(
            created_by=self.user,
            validated_data={
                "supplier": self.supplier,
                "reference": "PO-100",
                "items": [
                    {
                        "product": self.product,
                        "quantity": 2,
                        "unit_purchase_price": Decimal("20.00"),
                    }
                ],
            },
        )

    def test_update_draft(self):
        UpdatePurchase()(
            purchase_id=self.purchase.pk,
            actor=self.user,
            validated_data={
                "reference": "PO-101",
                "items": [
                    {
                        "product": self.product,
                        "quantity": 4,
                        "unit_purchase_price": Decimal("19.00"),
                    }
                ],
            },
        )
        self.purchase.refresh_from_db()
        self.assertEqual(self.purchase.reference, "PO-101")
        self.assertEqual(self.purchase.items.get().quantity, 4)

    def test_delete_draft(self):
        DeletePurchase()(purchase_id=self.purchase.pk, actor=self.user)
        self.assertFalse(Purchase.objects.filter(pk=self.purchase.pk).exists())

    def test_update_confirmed_purchase_is_rejected(self):
        self.purchase.status = Purchase.Status.CONFIRMED
        self.purchase.save(update_fields=("status",))
        with self.assertRaises(InvalidBusinessOperation):
            UpdatePurchase()(
                purchase_id=self.purchase.pk,
                actor=self.user,
                validated_data={"reference": "blocked"},
            )

    def test_inactive_product_is_rejected(self):
        self.product.is_active = False
        self.product.save(update_fields=("is_active",))
        with self.assertRaises(InvalidBusinessOperation):
            CreatePurchase()(
                created_by=self.user,
                validated_data={
                    "supplier": self.supplier,
                    "items": [
                        {
                            "product": self.product,
                            "quantity": 1,
                            "unit_purchase_price": Decimal("20.00"),
                        }
                    ],
                },
            )
