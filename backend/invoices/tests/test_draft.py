from decimal import Decimal

from django.test import TestCase

from common.exceptions import InvalidBusinessOperation, InvalidStateTransition
from coupons.models import Coupon
from invoices.models import Invoice, InvoiceItem
from invoices.services import ApplyCoupon, DeleteInvoice, RemoveCoupon, UpdateInvoice

from .helpers import InvoiceTestMixin


class InvoiceDraftTests(InvoiceTestMixin, TestCase):
    def create_invoice(self):
        invoice = Invoice.objects.create(customer=self.customer, created_by=self.user)
        InvoiceItem.objects.create(
            invoice=invoice,
            product=self.product,
            quantity=2,
            unit_price=Decimal("100.00"),
        )
        return invoice

    def test_update_replaces_draft_items_and_snapshots_price(self):
        invoice = self.create_invoice()
        second = self.product.__class__.objects.create(
            name="Second",
            purchase_price=Decimal("20.00"),
            selling_price=Decimal("40.00"),
        )

        UpdateInvoice()(
            invoice_id=invoice.pk,
            validated_data={"items": [{"product": second, "quantity": 3}]},
            actor=self.user,
        )

        item = invoice.items.get()
        self.assertEqual(item.product, second)
        self.assertEqual(item.unit_price, Decimal("40.00"))

    def test_update_rejects_inactive_product(self):
        invoice = self.create_invoice()
        self.product.is_active = False
        self.product.save(update_fields=("is_active",))

        with self.assertRaises(InvalidBusinessOperation):
            UpdateInvoice()(
                invoice_id=invoice.pk,
                validated_data={"items": [{"product": self.product, "quantity": 1}]},
                actor=self.user,
            )

    def test_coupon_apply_remove(self):
        invoice = self.create_invoice()
        coupon = Coupon.objects.create(
            code="SAVE10",
            discount_type=Coupon.DiscountType.PERCENTAGE,
            discount_value=Decimal("10.00"),
        )

        ApplyCoupon()(invoice_id=invoice.pk, code=coupon.code, actor=self.user)
        invoice.refresh_from_db()
        self.assertEqual(invoice.coupon_id, coupon.pk)
        self.assertEqual(invoice.coupon_discount, Decimal("20.00"))

        RemoveCoupon()(invoice_id=invoice.pk, actor=self.user)
        invoice.refresh_from_db()
        self.assertIsNone(invoice.coupon_id)
        self.assertEqual(invoice.coupon_discount, Decimal("0.00"))

    def test_delete_only_draft(self):
        invoice = self.create_invoice()
        DeleteInvoice()(invoice_id=invoice.pk, actor=self.user)
        self.assertFalse(Invoice.objects.filter(pk=invoice.pk).exists())

    def test_update_non_draft_rejected(self):
        invoice = self.create_invoice()
        invoice.status = Invoice.Status.CONFIRMED
        invoice.save(update_fields=("status",))

        with self.assertRaises(InvalidBusinessOperation):
            UpdateInvoice()(
                invoice_id=invoice.pk,
                validated_data={"items": []},
                actor=self.user,
            )

    def test_remove_coupon_non_draft_rejected(self):
        invoice = self.create_invoice()
        invoice.status = Invoice.Status.CONFIRMED
        invoice.save(update_fields=("status",))

        with self.assertRaises(InvalidStateTransition):
            RemoveCoupon()(invoice_id=invoice.pk, actor=self.user)
