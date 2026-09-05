from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase

from customers.models import Customer
from inventory.models import StockLocation
from products.models import Product


class InvoiceTestMixin:
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(
            username="invoice-user",
            email="invoice@example.com",
            password="StrongPass123!",
            is_staff=True,
        )
        self.customer = Customer.objects.create(name="Acme")
        self.product = Product.objects.create(
            name="Widget",
            purchase_price=Decimal("50.00"),
            selling_price=Decimal("100.00"),
        )
        self.location = StockLocation.objects.create(
            name="Van 01",
            location_type=StockLocation.LocationType.SALES_VEHICLE,
            employee=self.user,
        )


class InvoiceModelTestCase(InvoiceTestMixin, TestCase):
    pass
