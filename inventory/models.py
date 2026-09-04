from django.conf import settings
from django.db import models
from django.db.models import Q

from products.models import Product


class StockLocation(models.Model):
    class LocationType(models.TextChoices):
        MAIN_WAREHOUSE = "MAIN_WAREHOUSE", "Main Warehouse"
        SALES_VEHICLE = "SALES_VEHICLE", "Sales Vehicle"

    name = models.CharField(max_length=150)
    location_type = models.CharField(
        max_length=30,
        choices=LocationType.choices,
    )
    employee = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="stock_location",
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("name",)
        constraints = [
            models.UniqueConstraint(
                fields=("location_type",),
                condition=Q(
                    location_type="MAIN_WAREHOUSE",
                    is_active=True,
                ),
                name="inventory_one_active_main_warehouse",
            ),
        ]

    def __str__(self):
        return self.name


class StockMovement(models.Model):
    class MovementType(models.TextChoices):
        PURCHASE = "PURCHASE", "Purchase"
        TRANSFER = "TRANSFER", "Transfer"
        SALE = "SALE", "Sale"
        SALEABLE_RETURN = "SALEABLE_RETURN", "Saleable Return"
        DAMAGED_RETURN = "DAMAGED_RETURN", "Damaged Return"

    movement_type = models.CharField(
        max_length=30,
        choices=MovementType.choices,
    )
    source_location = models.ForeignKey(
        StockLocation,
        on_delete=models.PROTECT,
        related_name="outgoing_movements",
        null=True,
        blank=True,
    )
    destination_location = models.ForeignKey(
        StockLocation,
        on_delete=models.PROTECT,
        related_name="incoming_movements",
        null=True,
        blank=True,
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="created_stock_movements",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    reference = models.CharField(
        max_length=100,
        blank=True,
    )

    class Meta:
        ordering = ("-created_at",)

    def __str__(self):
        return f"{self.get_movement_type_display()} #{self.pk}"


class StockMovementItem(models.Model):
    movement = models.ForeignKey(
        StockMovement,
        on_delete=models.CASCADE,
        related_name="items",
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.PROTECT,
        related_name="stock_movement_items",
    )
    quantity = models.PositiveIntegerField()

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=Q(quantity__gte=1),
                name="stock_movement_item_quantity_positive",
            ),
        ]
        ordering = ("id",)

    def __str__(self):
        return f"{self.product} x {self.quantity}"


class StockBalance(models.Model):
    location = models.ForeignKey(
        StockLocation,
        on_delete=models.CASCADE,
        related_name="stock_balances",
    )
    product = models.ForeignKey(
        "products.Product",
        on_delete=models.PROTECT,
        related_name="stock_balances",
    )
    quantity = models.PositiveIntegerField(default=0)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("location", "product"),
                name="stock_balance_unique_location_product",
            ),
        ]

    def __str__(self):
        return f"{self.location_id} - {self.product_id}: {self.quantity}"
