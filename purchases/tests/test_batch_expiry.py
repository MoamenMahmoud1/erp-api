from datetime import date, timedelta
from decimal import Decimal

from django.test import TestCase

from inventory.models import InventoryBatch, StockBatchBalance
from organization.models import Company
from products.models import Product
from purchases.models import Purchase, PurchaseItem
from purchases.services.confirm_purchase import ConfirmPurchaseService
from suppliers.models import Supplier
from accounts.models import CustomUserModel


class PurchaseBatchExpiryTests(TestCase):
    def setUp(self):
        self.user = CustomUserModel.objects.create_user(
            username="batch-purchase-user",
            email="batch-purchase@example.com",
            password="StrongPass123!",
            is_staff=True,
        )
        self.company = Company.objects.create(name="Batch Purchase Company")
        self.supplier = Supplier.objects.create(name="Batch Supplier")
        self.product = Product.objects.create(
            name="Milk",
            purchase_price=Decimal("20.00"),
            selling_price=Decimal("30.00"),
        )

    def test_confirm_creates_batch_with_purchase_dates(self):
        production = date.today() - timedelta(days=3)
        expiry = date.today() + timedelta(days=27)
        purchase = Purchase.objects.create(supplier=self.supplier, created_by=self.user, reference="BATCH-PO-1")
        PurchaseItem.objects.create(
            purchase=purchase,
            product=self.product,
            quantity=12,
            unit_purchase_price=Decimal("18.50"),
            batch_number="MILK-001",
            manufactured_date=production,
            expiry_date=expiry,
        )

        ConfirmPurchaseService.execute(purchase_id=purchase.pk, actor=self.user)

        purchase_item = PurchaseItem.objects.get(purchase=purchase, product=self.product)
        self.assertIsNotNone(purchase_item.batch_id)
        batch = purchase_item.batch
        self.assertEqual(batch.batch_number, "MILK-001")
        self.assertEqual(batch.manufactured_date, production)
        self.assertEqual(batch.expiry_date, expiry)
        self.assertEqual(InventoryBatch.objects.filter(product=self.product, batch_number="MILK-001").count(), 1)
        stock = StockBatchBalance.objects.get(batch=batch)
        self.assertEqual(stock.quantity, 12)
        self.assertEqual(stock.total_cost, Decimal("222.00"))

    def test_same_batch_can_be_received_again_when_dates_match(self):
        expiry = date.today() + timedelta(days=20)
        first = Purchase.objects.create(supplier=self.supplier, created_by=self.user, reference="BATCH-PO-2")
        PurchaseItem.objects.create(purchase=first, product=self.product, quantity=5, unit_purchase_price=Decimal("10"), batch_number="LOT-X", expiry_date=expiry)
        ConfirmPurchaseService.execute(purchase_id=first.pk, actor=self.user)

        second = Purchase.objects.create(supplier=self.supplier, created_by=self.user, reference="BATCH-PO-3")
        PurchaseItem.objects.create(purchase=second, product=self.product, quantity=7, unit_purchase_price=Decimal("11"), batch_number="LOT-X", expiry_date=expiry)
        ConfirmPurchaseService.execute(purchase_id=second.pk, actor=self.user)

        self.assertEqual(InventoryBatch.objects.filter(product=self.product, batch_number="LOT-X").count(), 1)
        batch = InventoryBatch.objects.get(product=self.product, batch_number="LOT-X")
        self.assertEqual(StockBatchBalance.objects.get(batch=batch).quantity, 12)
