from decimal import Decimal

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import Q

from invoices.calculator import InvoiceCalculator

_calculator = InvoiceCalculator()


class Invoice(models.Model):
    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        CONFIRMED = "confirmed", "Confirmed"
        CANCELLED = "cancelled", "Cancelled"
        PAID = "paid", "Paid"

    customer = models.ForeignKey(
        "customers.Customer",
        on_delete=models.PROTECT,
        related_name="invoices",
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="created_invoices",
    )
    coupon = models.ForeignKey(
        "coupons.Coupon",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
    )
    coupon_discount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0"),
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT,
        db_index=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-created_at",)
        indexes = [
            models.Index(
                fields=("customer", "created_at"),
                name="invoice_cust_created_idx",
            )
        ]
        permissions = [
            ("confirm_invoice", "Can confirm an invoice"),
            ("cancel_invoice", "Can cancel an invoice"),
            ("apply_invoice_coupon", "Can apply a coupon to an invoice"),
        ]
        constraints = [
            models.CheckConstraint(
                condition=Q(coupon_discount__gte=Decimal("0")),
                name="invoice_coupon_discount_non_negative",
            ),
        ]

    @property
    def subtotal(self):
        return _calculator.subtotal(self)

    @property
    def discount(self):
        return _calculator.discount(self)

    @property
    def total(self):
        return _calculator.total(self)

    @property
    def sold_quantity(self):
        return sum(item.quantity for item in self.items.all())

    @property
    def paid_amount(self):
        """Authoritative paid amount = sum of payment allocations.

        Derived from ``PaymentAllocation`` rows — never independently editable.
        """
        from common.money import quantize_money

        return quantize_money(
            sum(
                (allocation.total_amount for allocation in self.payment_allocations.all()),
                Decimal("0"),
            )
        )

    @property
    def outstanding_amount(self):
        """Remaining balance = total - paid_amount (no silent negative clamp)."""
        from common.money import quantize_money

        return quantize_money(self.total - self.paid_amount)


class InvoiceItem(models.Model):
    invoice = models.ForeignKey(
        Invoice,
        on_delete=models.CASCADE,
        related_name="items",
    )
    product = models.ForeignKey(
        "products.Product",
        on_delete=models.PROTECT,
        related_name="invoice_items",
    )
    quantity = models.PositiveIntegerField(
        validators=[MinValueValidator(1)]
    )
    unit_price = models.DecimalField(max_digits=12, decimal_places=2)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("invoice", "product"),
                name="invoices_unique_invoice_product",
            ),
            models.CheckConstraint(
                condition=Q(quantity__gte=1),
                name="invoice_item_quantity_positive",
            ),
            models.CheckConstraint(
                condition=Q(unit_price__gte=Decimal("0")),
                name="invoice_item_unit_price_non_negative",
            ),
        ]

    @property
    def line_total(self):
        from common.money import quantize_money

        return quantize_money(self.unit_price * self.quantity)