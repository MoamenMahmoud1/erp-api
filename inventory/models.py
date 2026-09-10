from decimal import Decimal

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import F, Q
from django.utils import timezone

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
    warehouse_managers = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        blank=True,
        related_name="managed_warehouses",
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


class InventoryBatch(models.Model):
    product = models.ForeignKey(Product, on_delete=models.PROTECT, related_name="inventory_batches")
    batch_number = models.CharField(max_length=100, null=True, blank=True)
    manufactured_date = models.DateField(null=True, blank=True)
    expiry_date = models.DateField(null=True, blank=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("expiry_date", "id")
        indexes = [
            models.Index(fields=("product", "expiry_date"), name="inventory_batch_expiry_idx"),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=("product", "batch_number"),
                condition=Q(batch_number__isnull=False),
                name="inventory_batch_product_number_unique",
            ),
            models.CheckConstraint(
                condition=Q(expiry_date__isnull=True)
                | Q(manufactured_date__isnull=True)
                | Q(expiry_date__gte=F("manufactured_date")),
                name="inventory_batch_dates_ordered",
            ),
        ]

    @property
    def is_expired(self):
        return self.expiry_date is not None and self.expiry_date < timezone.localdate()

    @property
    def days_to_expiry(self):
        if self.expiry_date is None:
            return None
        return (self.expiry_date - timezone.localdate()).days

    def __str__(self):
        label = self.batch_number or f"Batch #{self.pk}"
        return f"{self.product.name} · {label}"


class StockBatchBalance(models.Model):
    location = models.ForeignKey(StockLocation, on_delete=models.CASCADE, related_name="stock_batch_balances")
    batch = models.ForeignKey(InventoryBatch, on_delete=models.PROTECT, related_name="stock_balances")
    quantity = models.PositiveIntegerField(default=0)
    total_cost = models.DecimalField(max_digits=16, decimal_places=2, default=Decimal("0.00"), validators=[MinValueValidator(Decimal("0"))])
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("batch__expiry_date", "batch_id")
        constraints = [
            models.UniqueConstraint(fields=("location", "batch"), name="stock_batch_balance_unique_location_batch"),
            models.CheckConstraint(condition=Q(quantity__gte=0), name="stock_batch_balance_quantity_non_negative"),
            models.CheckConstraint(condition=Q(total_cost__gte=Decimal("0")), name="stock_batch_balance_total_cost_non_negative"),
        ]
        indexes = [
            models.Index(fields=("location", "quantity"), name="sbb_loc_qty_idx"),
            models.Index(fields=("batch", "location"), name="sbb_batch_loc_idx"),
        ]

    @property
    def product(self):
        return self.batch.product

    @property
    def average_unit_cost(self):
        if not self.quantity:
            return Decimal("0.00")
        return self.total_cost / Decimal(self.quantity)

    def __str__(self):
        return f"{self.location_id} - {self.batch_id}: {self.quantity}"


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
            ("approve_stock_transfer", "Can approve stock transfer requests"),
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
    batch = models.ForeignKey(InventoryBatch, on_delete=models.PROTECT, null=True, blank=True, related_name="movement_items")
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
        batch_label = f" · {self.batch.batch_number}" if self.batch_id and self.batch.batch_number else ""
        return f"{self.product} x {self.quantity}{batch_label}"


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


class StockTransferRequest(models.Model):
    class RequestType(models.TextChoices):
        WAREHOUSE_TO_VEHICLE = "WAREHOUSE_TO_VEHICLE", "Warehouse to vehicle"
        VEHICLE_TO_WAREHOUSE = "VEHICLE_TO_WAREHOUSE", "Vehicle to warehouse"

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"
        CANCELLED = "cancelled", "Cancelled"

    request_type = models.CharField(max_length=30, choices=RequestType.choices)
    requested_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="stock_transfer_requests")
    warehouse_manager = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="warehouse_transfer_requests")
    approved_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, null=True, blank=True, related_name="approved_stock_transfer_requests")
    shift = models.ForeignKey("accounts.EmployeeShift", on_delete=models.PROTECT, related_name="stock_transfer_requests")
    warehouse = models.ForeignKey(StockLocation, on_delete=models.PROTECT, related_name="stock_transfer_requests", limit_choices_to={"location_type": "MAIN_WAREHOUSE"})
    source_location = models.ForeignKey(StockLocation, on_delete=models.PROTECT, related_name="source_stock_transfer_requests")
    destination_location = models.ForeignKey(StockLocation, on_delete=models.PROTECT, related_name="destination_stock_transfer_requests")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING, db_index=True)
    reference = models.CharField(max_length=100, blank=True)
    rejection_reason = models.CharField(max_length=500, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    approved_movement = models.ForeignKey(StockMovement, on_delete=models.PROTECT, null=True, blank=True, related_name="approved_transfer_requests")
    invoice_return = models.ForeignKey("invoices.InvoiceReturn", on_delete=models.PROTECT, null=True, blank=True, related_name="stock_transfer_request")

    class Meta:
        ordering = ("-created_at", "-id")
        indexes = [
            models.Index(fields=("warehouse_manager", "status", "created_at"), name="stock_req_mgr_status_idx"),
            models.Index(fields=("requested_by", "status", "created_at"), name="stock_req_user_status_idx"),
            models.Index(fields=("warehouse", "status", "created_at"), name="stock_req_wh_status_idx"),
        ]
        constraints = [
            models.CheckConstraint(
                condition=Q(source_location=F("warehouse")) | Q(destination_location=F("warehouse")),
                name="stock_req_warehouse_participates",
            ),
            models.CheckConstraint(
                condition=~Q(source_location=F("destination_location")),
                name="stock_req_locations_differ",
            ),
        ]

    def __str__(self):
        return f"Stock transfer request #{self.pk}"


class StockTransferRequestItem(models.Model):
    request = models.ForeignKey(StockTransferRequest, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey(Product, on_delete=models.PROTECT, related_name="stock_transfer_request_items")
    quantity = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    invoice_item = models.ForeignKey("invoices.InvoiceItem", on_delete=models.PROTECT, null=True, blank=True, related_name="stock_transfer_request_items")

    class Meta:
        ordering = ("id",)
        constraints = [
            models.CheckConstraint(condition=Q(quantity__gte=1), name="stock_req_item_quantity_positive"),
            models.UniqueConstraint(fields=("request", "product"), name="stock_req_item_unique_product"),
        ]

    def __str__(self):
        return f"{self.product} x {self.quantity}"
