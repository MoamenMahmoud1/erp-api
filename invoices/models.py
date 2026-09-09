from decimal import Decimal

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import Q

from invoices.calculator import InvoiceCalculator
from invoices.querysets import InvoiceQuerySet

_calculator = InvoiceCalculator()


class Invoice(models.Model):
    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        CONFIRMED = "confirmed", "Confirmed"
        CANCELLED = "cancelled", "Cancelled"
        PAID = "paid", "Paid"
        RETURNED = "returned", "Returned"

    customer = models.ForeignKey("customers.Customer", on_delete=models.PROTECT, related_name="invoices")
    site = models.ForeignKey(
        "organization.Site",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="invoices",
    )
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="created_invoices")
    coupon = models.ForeignKey("coupons.Coupon", null=True, blank=True, on_delete=models.PROTECT)
    coupon_discount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0"))
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    objects = InvoiceQuerySet.as_manager()

    class Meta:
        ordering = ("-created_at",)
        indexes = [
            models.Index(fields=("customer", "created_at"), name="invoice_cust_created_idx"),
            models.Index(fields=("site", "created_at"), name="invoice_site_created_idx"),
        ]
        permissions = [
            ("confirm_invoice", "Can confirm an invoice"),
            ("cancel_invoice", "Can cancel an invoice"),
            ("apply_invoice_coupon", "Can apply a coupon to an invoice"),
            ("return_invoice", "Can return items from a paid invoice"),
        ]
        constraints = [
            models.CheckConstraint(condition=Q(coupon_discount__gte=Decimal("0")), name="invoice_coupon_discount_non_negative"),
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
        quantity = Decimal("0")
        for item in self.items.all():
            returned = sum(value.quantity for value in item.return_items.all())
            quantity += item.quantity - returned
        return int(quantity)

    @property
    def paid_amount(self):
        from common.money import quantize_money
        return quantize_money(sum((item.total_amount for item in self.payment_allocations.all()), Decimal("0")))

    @property
    def refunded_amount(self):
        from common.money import quantize_money
        return quantize_money(sum((item.total_amount for item in self.payment_refunds.all()), Decimal("0")))

    @property
    def net_paid_amount(self):
        from common.money import quantize_money
        return quantize_money(self.paid_amount - self.refunded_amount)

    @property
    def returned_amount(self):
        from common.money import quantize_money
        return quantize_money(sum((item.refund_amount for item in self.returns.all()), Decimal("0")))

    @property
    def outstanding_amount(self):
        from common.money import quantize_money
        return quantize_money(self.total - self.paid_amount)


class InvoiceItem(models.Model):
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey("products.Product", on_delete=models.PROTECT, related_name="invoice_items")
    quantity = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    unit_price = models.DecimalField(max_digits=12, decimal_places=2)
    cost_price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal("0"))],
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=("invoice", "product"), name="invoices_unique_invoice_product"),
            models.CheckConstraint(condition=Q(quantity__gte=1), name="invoice_item_quantity_positive"),
            models.CheckConstraint(condition=Q(unit_price__gte=Decimal("0")), name="invoice_item_unit_price_non_negative"),
            models.CheckConstraint(condition=Q(cost_price__gte=Decimal("0")) | Q(cost_price__isnull=True), name="invoice_item_cost_price_non_negative"),
        ]

    @property
    def line_total(self):
        from common.money import quantize_money
        return quantize_money(self.unit_price * self.quantity)


class InvoiceReturn(models.Model):
    invoice = models.ForeignKey(Invoice, on_delete=models.PROTECT, related_name="returns")
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="created_invoice_returns")
    reason = models.CharField(max_length=255, blank=True)
    refund_amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0"), validators=[MinValueValidator(Decimal("0"))])
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-created_at",)
        constraints = [
            models.CheckConstraint(condition=Q(refund_amount__gte=Decimal("0")), name="invoice_return_refund_amount_non_negative"),
        ]

    @property
    def merchandise_amount(self):
        from common.money import quantize_money
        return quantize_money(sum((item.line_total for item in self.items.all()), Decimal("0")))

    @property
    def total_amount(self):
        return self.refund_amount


class InvoiceReturnItem(models.Model):
    class Condition(models.TextChoices):
        SALEABLE = "saleable", "Saleable"

    invoice_return = models.ForeignKey(InvoiceReturn, on_delete=models.CASCADE, related_name="items")
    invoice_item = models.ForeignKey(InvoiceItem, on_delete=models.PROTECT, related_name="return_items")
    quantity = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    condition = models.CharField(max_length=20, choices=Condition.choices, default=Condition.SALEABLE)
    unit_price = models.DecimalField(max_digits=12, decimal_places=2)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=("invoice_return", "invoice_item"), name="invoice_return_item_unique_line"),
            models.CheckConstraint(condition=Q(quantity__gte=1), name="invoice_return_item_quantity_positive"),
            models.CheckConstraint(condition=Q(unit_price__gte=0), name="invoice_return_item_price_non_negative"),
        ]

    @property
    def line_total(self):
        from common.money import quantize_money
        return quantize_money(self.unit_price * self.quantity)
