from datetime import timedelta
from decimal import Decimal

from django.test import TestCase
from django.utils import timezone

from accounting.services.analytics import (
    inventory_dashboard,
    purchase_dashboard,
    sales_by_employee,
    sales_dashboard,
    top_products,
)
from accounts.models import CustomUserModel
from customers.models import Customer
from inventory.models import StockBalance, StockLocation
from invoices.models import Invoice, InvoiceItem
from products.models import Product
from purchases.models import Purchase, PurchaseItem
from suppliers.models import Supplier


class AnalyticsTests(TestCase):
    def setUp(self):
        self.user = CustomUserModel.objects.create_user(
            email="analytics@test.local",
            password="strong-password-123",
        )
        self.user_two = CustomUserModel.objects.create_user(
            email="analytics-two@test.local",
            password="strong-password-123",
        )
        self.customer = Customer.objects.create(name="Analytics Customer")
        self.supplier = Supplier.objects.create(name="Analytics Supplier")
        self.product_a = Product.objects.create(
            name="Product A",
            purchase_price=Decimal("40"),
            selling_price=Decimal("100"),
        )
        self.product_b = Product.objects.create(
            name="Product B",
            purchase_price=Decimal("20"),
            selling_price=Decimal("50"),
        )
        self.location = StockLocation.objects.create(
            name="Analytics Warehouse",
            location_type=StockLocation.LocationType.MAIN_WAREHOUSE,
        )

    def _invoice(self, user, *, product, quantity, price, days_ago=0, discount=Decimal("0")):
        invoice = Invoice.objects.create(
            customer=self.customer,
            created_by=user,
            status=Invoice.Status.PAID,
            coupon_discount=discount,
        )
        InvoiceItem.objects.create(
            invoice=invoice,
            product=product,
            quantity=quantity,
            unit_price=Decimal(price),
        )
        created_at = timezone.now() - timedelta(days=days_ago)
        Invoice.objects.filter(pk=invoice.pk).update(created_at=created_at)
        return invoice

    def _purchase(self, *, product, quantity, price, days_ago=0):
        purchase = Purchase.objects.create(
            supplier=self.supplier,
            created_by=self.user,
            status=Purchase.Status.CONFIRMED,
        )
        PurchaseItem.objects.create(
            purchase=purchase,
            product=product,
            quantity=quantity,
            unit_purchase_price=Decimal(price),
        )
        created_at = timezone.now() - timedelta(days=days_ago)
        Purchase.objects.filter(pk=purchase.pk).update(created_at=created_at)
        return purchase

    def test_sales_dashboard_respects_date_range_and_discount(self):
        self._invoice(
            self.user,
            product=self.product_a,
            quantity=3,
            price="100",
            discount=Decimal("20"),
        )
        self._invoice(
            self.user,
            product=self.product_b,
            quantity=2,
            price="50",
            days_ago=10,
        )
        result = sales_dashboard(
            date_from=timezone.localdate() - timedelta(days=2),
            date_to=timezone.localdate(),
        )
        self.assertEqual(result["gross_sales"], Decimal("280"))
        self.assertEqual(result["units_sold"], 3)
        self.assertEqual(result["invoice_count"], 1)

    def test_purchase_dashboard(self):
        self._purchase(product=self.product_a, quantity=4, price="40")
        result = purchase_dashboard(
            date_from=timezone.localdate() - timedelta(days=1),
            date_to=timezone.localdate(),
        )
        self.assertEqual(result["purchase_value"], Decimal("160"))
        self.assertEqual(result["units_purchased"], 4)
        self.assertEqual(result["purchase_count"], 1)

    def test_inventory_dashboard_reports_value_and_low_stock(self):
        StockBalance.objects.create(location=self.location, product=self.product_a, quantity=25)
        StockBalance.objects.create(location=self.location, product=self.product_b, quantity=5)
        result = inventory_dashboard(low_stock_threshold=10)
        self.assertEqual(result["product_count"], 2)
        self.assertEqual(result["total_units"], 30)
        self.assertEqual(result["inventory_value"], Decimal("1100"))
        self.assertEqual(result["low_stock_count"], 1)
        self.assertEqual(result["low_stock"][0]["product_id"], self.product_b.pk)

    def test_top_products_orders_by_quantity(self):
        self._invoice(self.user, product=self.product_a, quantity=5, price="100")
        self._invoice(self.user_two, product=self.product_b, quantity=8, price="50")
        result = top_products(limit=2)
        self.assertEqual([row["product_id"] for row in result], [self.product_b.pk, self.product_a.pk])
        self.assertEqual(result[0]["quantity"], 8)
        self.assertEqual(result[0]["revenue"], Decimal("400"))

    def test_sales_by_employee(self):
        self._invoice(self.user, product=self.product_a, quantity=2, price="100")
        self._invoice(self.user_two, product=self.product_b, quantity=5, price="50")
        result = sales_by_employee()
        self.assertEqual(result[0]["invoice__created_by_id"], self.user_two.pk)
        self.assertEqual(result[0]["revenue"], Decimal("250"))
        self.assertEqual(result[1]["invoice__created_by_id"], self.user.pk)
        self.assertEqual(result[1]["revenue"], Decimal("200"))
