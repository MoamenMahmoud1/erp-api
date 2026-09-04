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

    supplier = models.ForeignKey(
        "suppliers.Supplier",
        on_delete=models.PROTECT,
        related_name="purchases",
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT,
    )
    reference = models.CharField(
        max_length=100,
        blank=True,
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="created_purchases",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = PurchaseQuerySet.as_manager()

    class Meta:
        ordering = ("-created_at",)
        permissions = [
            ("confirm_purchase", "Can confirm purchase"),
            ("cancel_purchase", "Can cancel purchase"),
        ]

    def __str__(self):
        return f"Purchase #{self.pk}"

    @property
    def total_amount(self) -> Decimal:
        return sum(
            (item.total_amount for item in self.items.all()),
            Decimal("0.00"),
        )


class PurchaseItem(models.Model):
    purchase = models.ForeignKey(
        Purchase,
        on_delete=models.CASCADE,
        related_name="items",
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.PROTECT,
        related_name="purchase_items",
    )
    quantity = models.PositiveIntegerField(
        validators=[MinValueValidator(1)],
    )
    unit_purchase_price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0"))],
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("purchase", "product"),
                name="purchase_item_unique_product",
            ),
            models.CheckConstraint(
                condition=Q(quantity__gte=1),
                name="purchase_item_quantity_positive",
            ),
            models.CheckConstraint(
                condition=Q(unit_purchase_price__gte=0),
                name="purchase_item_price_non_negative",
            ),
        ]
        ordering = ("id",)

    def __str__(self):
        return f"{self.product} x {self.quantity}"

    @property
    def total_amount(self) -> Decimal:
        return self.unit_purchase_price * self.quantity
