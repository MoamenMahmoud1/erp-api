from decimal import Decimal

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission

from accounts.models import Employee
from customers.models import Customer
from invoices.models import Invoice, InvoiceItem
from organization.models import Company, Site
from products.models import Product


class PaymentTestMixin:
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="cashier",
            email="cashier@example.com",
            password="StrongPass123!",
            is_staff=True,
        )
        payment_permissions = Permission.objects.filter(
            content_type__app_label="payments",
        )
        self.user.user_permissions.add(*payment_permissions)
        self.company = Company.objects.create(name="Payment Test Company")
        self.site = Site.objects.create(
            company=self.company,
            code="PAY-BR",
            name="Payment Test Branch",
            site_type=Site.Type.BRANCH,
            address_line_1="Test address",
            city="Cairo",
            country_code="EG",
        )
        Employee.objects.create(user=self.user, work_site=self.site)
        self.customer = Customer.objects.create(name="Acme")
        self.product = Product.objects.create(
            name="Widget",
            purchase_price=Decimal("50.00"),
            selling_price=Decimal("100.00"),
        )

    def create_invoice(self, *, total="100.00", status=Invoice.Status.CONFIRMED):
        invoice = Invoice.objects.create(
            customer=self.customer,
            site=self.site,
            created_by=self.user,
            status=status,
        )
        InvoiceItem.objects.create(
            invoice=invoice,
            product=self.product,
            quantity=1,
            unit_price=Decimal(total),
        )
        return invoice
