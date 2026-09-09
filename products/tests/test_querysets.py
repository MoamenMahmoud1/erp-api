from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase

from customers.models import Customer
from invoices.models import Invoice, InvoiceItem, InvoiceReturn, InvoiceReturnItem
from products.models import Product


class ProductQuerySetTests(TestCase):
    def test_with_stock_stats_excludes_returned_units(self):
        user = get_user_model().objects.create_user(username="seller", email="seller@test.com", password="StrongPass123!")
        customer = Customer.objects.create(name="Customer")
        product = Product.objects.create(name="Product", purchase_price=Decimal("10"), selling_price=Decimal("20"))
        invoice = Invoice.objects.create(customer=customer, created_by=user, status=Invoice.Status.PAID)
        invoice_item = InvoiceItem.objects.create(invoice=invoice, product=product, quantity=10, unit_price=Decimal("20"))
        sales_return = InvoiceReturn.objects.create(invoice=invoice, created_by=user, refund_amount=Decimal("60"))
        InvoiceReturnItem.objects.create(invoice_return=sales_return, invoice_item=invoice_item, quantity=3, unit_price=Decimal("20"))

        product = Product.objects.with_stock_stats().get(pk=product.pk)

        self.assertEqual(product._sold_quantity, 7)
