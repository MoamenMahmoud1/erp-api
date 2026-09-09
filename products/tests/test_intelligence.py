from datetime import timedelta
from decimal import Decimal

from django.core.cache import cache
from django.test import TestCase
from django.utils import timezone

from accounts.models import CustomUserModel
from customers.models import Customer
from inventory.models import StockBalance, StockLocation
from invoices.models import Invoice, InvoiceItem
from products.models import Product
from products.services.intelligence import product_intelligence


class ProductIntelligenceTests(TestCase):
    def setUp(self):
        cache.clear()
        self.user = CustomUserModel.objects.create_user(
            username="intelligence-user",
            email="intelligence@test.local",
            password="strong-password-123",
        )
        self.customer = Customer.objects.create(name="Intelligence Customer")
        self.product = Product.objects.create(
            name="Fast Charger",
            category="Accessories",
            purchase_price=Decimal("40"),
            selling_price=Decimal("100"),
        )
        self.slow_product = Product.objects.create(
            name="Slow Charger",
            category="Accessories",
            purchase_price=Decimal("20"),
            selling_price=Decimal("50"),
        )
        self.location = StockLocation.objects.create(
            name="Intelligence Warehouse",
            location_type=StockLocation.LocationType.MAIN_WAREHOUSE,
        )
        StockBalance.objects.create(
            product=self.product,
            location=self.location,
            quantity=2,
            total_cost=Decimal("80"),
        )
        StockBalance.objects.create(
            product=self.slow_product,
            location=self.location,
            quantity=20,
            total_cost=Decimal("400"),
        )

    def _sale(self, product, quantity, days_ago):
        invoice = Invoice.objects.create(
            customer=self.customer,
            created_by=self.user,
            status=Invoice.Status.PAID,
        )
        InvoiceItem.objects.create(
            invoice=invoice,
            product=product,
            quantity=quantity,
            unit_price=product.selling_price,
        )
        Invoice.objects.filter(pk=invoice.pk).update(
            created_at=timezone.now() - timedelta(days=days_ago),
        )

    def test_reorder_and_slow_moving_recommendations(self):
        self._sale(self.product, 10, 3)
        self._sale(self.product, 5, 40)

        result = product_intelligence(
            as_of=timezone.localdate(),
            lookback_days=30,
            forecast_days=7,
            target_stock_days=14,
            slow_moving_days=60,
        )

        fast = next(item for item in result["products"] if item["product_id"] == self.product.pk)
        slow = next(item for item in result["products"] if item["product_id"] == self.slow_product.pk)

        self.assertEqual(fast["sold_units"], 10)
        self.assertEqual(fast["average_daily_sales"], Decimal("0.33"))
        self.assertEqual(fast["stock_status"], "reorder")
        self.assertEqual(fast["reorder_quantity"], 3)
        self.assertEqual(fast["estimated_gross_profit"], Decimal("600.00"))
        self.assertEqual(fast["estimated_gross_margin_pct"], Decimal("60.00"))

        self.assertTrue(slow["slow_moving"])
        self.assertEqual(slow["stock_status"], "no_demand")
        self.assertEqual(result["summary"]["slow_moving_count"], 1)

    def test_product_filter_and_empty_product_catalog(self):
        result = product_intelligence(product_id=self.product.pk, as_of=timezone.localdate())
        self.assertEqual(result["summary"]["product_count"], 1)
        self.assertEqual(result["products"][0]["product_id"], self.product.pk)

        self.slow_product.is_active = False
        self.slow_product.save(update_fields=["is_active"])
        cache.clear()
        result = product_intelligence(as_of=timezone.localdate())
        self.assertEqual(result["summary"]["product_count"], 1)
