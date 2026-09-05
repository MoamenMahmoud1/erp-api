from decimal import Decimal

from django.contrib.auth import get_user_model

from customers.models import Customer
from invoices.models import Invoice, InvoiceItem
from products.models import Product


class PaymentTestMixin:
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="cashier",
            email="cashier@example.com",
            password="StrongPass123!",
            is_staff=True,
        )
        self.customer = Customer.objects.create(name="Acme")
        self.product = Product.objects.create(
            name="Widget",
            purchase_price=Decimal("50.00"),
            selling_price=Decimal("100.00"),
        )

    def create_invoice(self, *, total="100.00", status=Invoice.Status.CONFIRMED):
        invoice = Invoice.objects.create(
            customer=self.customer,
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
