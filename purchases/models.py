from decimal import Decimal

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import Q

from products.models import Product
from purchases.querysets.purchase import PurchaseQuerySet


class Purchase(models.Model):
    class Status(models.TextChoices):
        DRAFT = "DRAFT", "Draft"
        CONFIRMED = "CONFIRMED", "Confirmed"
        CANCELLED = "CANCELLED", "Cancelled"

    supplier = models.ForeignKey("suppliers.Supplier", on_delete=models.PROTECT, related_name="purchases")
    site = models.ForeignKey(
        "organization.Site",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="purchases",
    )
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)
    reference = models.CharField(max_length=100, blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="created_purchases")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    objects = PurchaseQuerySet.as_manager()

    class Meta:
        ordering = ("-created_at",)
        indexes = [models.Index(fields=("site", "created_at"), name="purchase_site_created_idx")]
        permissions = [
            ("confirm_purchase", "Can confirm purchase"),
            ("cancel_purchase", "Can cancel purchase"),
            ("return_purchase", "Can return items from a purchase"),
            ("process_supplier_payment", "Can process a supplier payment"),
        ]

    def __str__(self):
        return f"Purchase #{self.pk}"

    @property
    def total_amount(self) -> Decimal:
        return sum((item.total_amount for item in self.items.all()), Decimal("0.00"))


class PurchaseItem(models.Model):
    purchase = models.ForeignKey(Purchase, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey(Product, on_delete=models.PROTECT, related_name="purchase_items")
    quantity = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    unit_purchase_price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0"))],
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=("purchase", "product"), name="purchase_item_unique_product"),
            models.CheckConstraint(condition=Q(quantity__gte=1), name="purchase_item_quantity_positive"),
            models.CheckConstraint(condition=Q(unit_purchase_price__gte=0), name="purchase_item_price_non_negative"),
        ]
        ordering = ("id",)

    @property
    def total_amount(self) -> Decimal:
        return self.unit_purchase_price * self.quantity


class PurchaseReturn(models.Model):
    purchase = models.ForeignKey(Purchase, on_delete=models.PROTECT, related_name="returns")
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="created_purchase_returns")
    reason = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-created_at",)

    @property
    def total_amount(self):
        return sum((item.line_total for item in self.items.all()), Decimal("0"))


class PurchaseReturnItem(models.Model):
    purchase_return = models.ForeignKey(PurchaseReturn, on_delete=models.CASCADE, related_name="items")
    purchase_item = models.ForeignKey(PurchaseItem, on_delete=models.PROTECT, related_name="return_items")
    quantity = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    unit_price = models.DecimalField(max_digits=12, decimal_places=2)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=("purchase_return", "purchase_item"), name="purchase_return_item_unique_line"),
            models.CheckConstraint(condition=Q(quantity__gte=1), name="purchase_return_item_quantity_positive"),
            models.CheckConstraint(condition=Q(unit_price__gte=0), name="purchase_return_item_price_non_negative"),
        ]

    @property
    def line_total(self):
        return self.unit_price * self.quantity


class SupplierPayment(models.Model):
    supplier = models.ForeignKey("suppliers.Supplier", on_delete=models.PROTECT, related_name="supplier_payments")
    paid_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="supplier_payments_made")
    cash_amount = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(Decimal("0"))])
    transfer_amount = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(Decimal("0"))])
    reference = models.CharField(max_length=100, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-created_at",)
        indexes = [
            models.Index(
                fields=("supplier", "created_at"),
                name="suppay_supplier_created_idx",
            )
        ]
        constraints = [
            models.CheckConstraint(condition=Q(cash_amount__gte=Decimal("0")), name="supplier_payment_cash_non_negative"),
            models.CheckConstraint(condition=Q(transfer_amount__gte=Decimal("0")), name="supplier_payment_transfer_non_negative"),
            models.CheckConstraint(
                condition=Q(cash_amount__gt=Decimal("0")) | Q(transfer_amount__gt=Decimal("0")),
                name="supplier_payment_amount_positive",
            ),
        ]

    @property
    def total_amount(self):
        return self.cash_amount + self.transfer_amount

    def __str__(self):
        return f"Supplier Payment #{self.pk}"


class SupplierPaymentAllocation(models.Model):
    payment = models.ForeignKey(SupplierPayment, on_delete=models.CASCADE, related_name="allocations")
    purchase = models.ForeignKey(Purchase, on_delete=models.PROTECT, related_name="supplier_payment_allocations")
    cash_amount = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(Decimal("0")))])
    transfer_amount = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(Decimal("0"))])
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("created_at", "id")
        constraints = [
            models.UniqueConstraint(fields=("payment", "purchase"), name="supplier_payment_alloc_payment_purchase_unique"),
            models.CheckConstraint(condition=Q(cash_amount__gte=Decimal("0")), name="supplier_payment_alloc_cash_non_negative"),
            models.CheckConstraint(condition=Q(transfer_amount__gte=Decimal("0")), name="supplier_payment_alloc_transfer_non_negative"),
            models.CheckConstraint(
                condition=Q(cash_amount__gt=Decimal("0")) | Q(transfer_amount__gt=Decimal("0")),
                name="supplier_payment_alloc_amount_positive",
            ),
        ]

    @property
    def total_amount(self):
        return self.cash_amount + self.transfer_amount

    def __str__(self):
        return f"Supplier Payment Allocation #{self.pk}"
