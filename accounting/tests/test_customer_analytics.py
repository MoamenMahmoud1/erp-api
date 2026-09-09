from decimal import Decimal

from django.test import TestCase

from accounting.services.analytics import customer_sales_ranking
from accounts.models import CustomUserModel
from customers.models import Customer
from invoices.models import Invoice, InvoiceItem
from products.models import Product


class CustomerAnalyticsTests(TestCase):
    def setUp(self):
        self.user = CustomUserModel.objects.create_user(
            username="customer-analytics-user",
            email="customer-analytics@example.com",
            password="StrongPass123!",
            is_staff=True,
        )
        self.product = Product.objects.create(name="Analytics Product", purchase_price=Decimal("10"), selling_price=Decimal("25"))
        self.top_customer = Customer.objects.create(name="Top Customer")
        self.bottom_customer = Customer.objects.create(name="Small Customer")

    def _invoice(self, customer, quantity, price):
        invoice = Invoice.objects.create(customer=customer, created_by=self.user, status=Invoice.Status.PAID)
        InvoiceItem.objects.create(invoice=invoice, product=self.product, quantity=quantity, unit_price=Decimal(price))

    def test_ranking_returns_highest_and_lowest_active_customers(self):
        self._invoice(self.top_customer, 10, "25")
        self._invoice(self.bottom_customer, 1, "25")

        top, bottom = customer_sales_ranking()

        self.assertEqual(top[0]["customer_id"], self.top_customer.pk)
        self.assertEqual(top[0]["revenue"], Decimal("250"))
        self.assertEqual(bottom[0]["customer_id"], self.bottom_customer.pk)
        self.assertEqual(bottom[0]["revenue"], Decimal("25"))
