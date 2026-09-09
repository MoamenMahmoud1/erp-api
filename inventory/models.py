from decimal import Decimal

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import F, Q

from inventory.querysets import StockLocationQuerySet, StockMovementQuerySet
from products.models import Product


class StockLocation(models.Model):
    class LocationType(models.TextChoices):
        MAIN_WAREHOUSE = "MAIN_WAREHOUSE", "Main Warehouse"
        SALES_VEHICLE = "SALES_VEHICLE", "Sales Vehicle"

    site = models.ForeignKey(
        "organization.Site",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="stock_locations",
    )
    name = models.CharField(max_length=150)
    location_type = models.CharField(max_length=30, choices=LocationType.choices)
    employee = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="stock_location",
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    objects = StockLocationQuerySet.as_manager()

    class Meta:
        ordering = ("name",)
        constraints = [
            models.UniqueConstraint(
                fields=("site",),
                condition=Q(site__isnull=False, location_type="MAIN_WAREHOUSE", is_active=True),
                name="inventory_one_active_main_warehouse_per_site",
            ),
            models.UniqueConstraint(
                fields=("location_type",),
                condition=Q(site__isnull=True, location_type="MAIN_WAREHOUSE", is_active=True),
                name="inventory_one_legacy_main_warehouse",
            ),
        ]

    def __str__(self):
        return self.name


class StockMovement(models.Model):
    class MovementType(models.TextChoices):
        PURCHASE = "PURCHASE", "Purchase"
        PURCHASE_RETURN = "PURCHASE_RETURN", "Purchase Return"
        TRANSFER = "TRANSFER", "Transfer"
        SALE = "SALE", "Sale"
        SALEABLE_RETURN = "SALEABLE_RETURN", "Saleable Return"
        DAMAGED_RETURN = "DAMAGED_RETURN", "Damaged Return"

    movement_type = models.CharField(max_length=30, choices=MovementType.choices)
    shift = models.ForeignKey(
        "accounts.EmployeeShift",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="stock_movements",
    )
    source_location = models.ForeignKey(StockLocation, on_delete=models.PROTECT, related_name="outgoing_movements", null=True, blank=True)
    destination_location = models.ForeignKey(StockLocation, on_delete=models.PROTECT, related_name="incoming_movements", null=True, blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="created_stock_movements")
    created_at = models.DateTimeField(auto_now_add=True)
    reference = models.CharField(max_length=100, blank=True)
    objects = StockMovementQuerySet.as_manager()

    class Meta:
        ordering = ("-created_at",)
        permissions = [
            ("transfer_stock", "Can transfer stock"),
        ]
        constraints = [
            models.CheckConstraint(
                condition=(
                    Q(movement_type="TRANSFER", source_location__isnull=False, destination_location__isnull=False)
                    | Q(movement_type__in=("PURCHASE_RETURN", "SALE"), source_location__isnull=False, destination_location__isnull=True)
                    | Q(movement_type__in=("PURCHASE", "SALEABLE_RETURN", "DAMAGED_RETURN"), source_location__isnull=True, destination_location__isnull=False)
                ),
                name="stock_movement_direction_matches_type",
            ),
            models.CheckConstraint(
                condition=(Q(movement_type="TRANSFER", source_location__isnull=True) | ~Q(source_location=F("destination_location"))),
                name="stock_transfer_locations_differ",
            ),
        ]

    def __str__(self):
        return f"{self.get_movement_type_display()} #{self.pk}"


class StockMovementItem(models.Model):
    movement = models.ForeignKey(StockMovement, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey(Product, on_delete=models.PROTECT, related_name="stock_movement_items")
    quantity = models.PositiveIntegerField()
    unit_cost = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True, validators=[MinValueValidator(Decimal("0"))], help_text="Historical inventory cost per unit captured at movement time.")

    class Meta:
        constraints = [
            models.CheckConstraint(condition=Q(quantity__gte=1), name="stock_movement_item_quantity_positive"),
            models.CheckConstraint(condition=Q(unit_cost__gte=0) | Q(unit_cost__isnull=True), name="stock_movement_item_unit_cost_non_negative"),
        ]
        indexes = [models.Index(fields=("product", "movement"), name="stock_move_item_product_idx")]
        ordering = ("id",)

    @property
    def total_cost(self):
        if self.unit_cost is None:
            return Decimal("0.00")
        return self.unit_cost * self.quantity

    def __str__(self):
        return f"{self.product} x {self.quantity}"


class StockBalance(models.Model):
    location = models.ForeignKey(StockLocation, on_delete=models.CASCADE, related_name="stock_balances")
    product = models.ForeignKey(Product, on_delete=models.PROTECT, related_name="stock_balances")
    quantity = models.PositiveIntegerField(default=0)
    total_cost = models.DecimalField(max_digits=16, decimal_places=2, default=Decimal("0.00"), validators=[MinValueValidator(Decimal("0"))])
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=("location", "product"), name="stock_balance_unique_location_product"),
            models.CheckConstraint(condition=Q(total_cost__gte=Decimal("0")), name="stock_balance_total_cost_non_negative"),
        ]

    @property
    def average_unit_cost(self):
        if not self.quantity:
            return Decimal("0.00")
        return self.total_cost / Decimal(self.quantity)

    def __str__(self):
        return f"{self.location_id} - {self.product_id}: {self.quantity}" 
