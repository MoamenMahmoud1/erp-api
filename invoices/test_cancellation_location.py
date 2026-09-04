from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase

from customers.models import Customer
from inventory.models import StockBalance, StockLocation
from invoices.models import Invoice, InvoiceItem
from invoices.services.lifecycle import _cancel_invoice_sync, _record_sale_movement_sync
from products.models import Product


class InvoiceCancellationOriginalLocationTests(TestCase):
    def test_confirmed_invoice_cancel_restores_original_sale_location(self):
        User = get_user_model()
        user = User.objects.create_user(
            username="location-move-user",
            email="location-move@example.com",
            password="StrongPass123!",
            is_staff=True,
        )
        customer = Customer.objects.create(name="Location Move Customer")
        product = Product.objects.create(
            name="Location Test Product",
            purchase_price=Decimal("10.00"),
            selling_price=Decimal("20.00"),
        )
        original = StockLocation.objects.create(
            name="Vehicle A",
            location_type=StockLocation.LocationType.SALES_VEHICLE,
            employee=user,
        )
        StockBalance.objects.create(
            location=original,
            product=product,
            quantity=10,
        )
        invoice = Invoice.objects.create(
            customer=customer,
            created_by=user,
            status=Invoice.Status.CONFIRMED,
        )
        InvoiceItem.objects.create(
            invoice=invoice,
            product=product,
            quantity=2,
            unit_price=Decimal("20.00"),
        )

        _record_sale_movement_sync(invoice, original)

        original.employee = None
        original.save(update_fields=("employee",))
        current = StockLocation.objects.create(
            name="Vehicle B",
            location_type=StockLocation.LocationType.SALES_VEHICLE,
            employee=user,
        )

        _cancel_invoice_sync(invoice.pk)

        self.assertEqual(
            StockBalance.objects.get(location=original, product=product).quantity,
            10,
        )
        self.assertFalse(
            StockBalance.objects.filter(location=current, product=product).exists()
        )
