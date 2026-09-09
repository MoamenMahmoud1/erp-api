from decimal import Decimal

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission

from customers.models import Customer
from inventory.models import StockLocation
from organization.models import Company
from products.models import Product


class InvoiceTestMixin:
    def setUp(self):
        User = get_user_model()
        self.company = Company.objects.create(name="Invoice Test Company")
        self.user = User.objects.create_user(
            username="invoice-user",
            email="invoice@example.com",
            password="StrongPass123!",
            is_staff=True,
        )
        invoice_permissions = Permission.objects.filter(
            content_type__app_label="invoices",
            content_type__model="invoice",
        )
        self.user.user_permissions.add(*invoice_permissions)
        custom_permissions = Permission.objects.filter(
            content_type__app_label="invoices",
            codename__in=(
                "confirm_invoice",
                "cancel_invoice",
                "apply_invoice_coupon",
                "return_invoice",
            ),
        )
        self.user.user_permissions.add(*custom_permissions)
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
