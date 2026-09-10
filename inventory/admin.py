from django.contrib import admin

from inventory.models import (
    StockBalance,
    StockBatchBalance,
    StockLocation,
    StockMovement,
    StockMovementItem,
    StockTransferRequest,
    StockTransferRequestItem,
)


@admin.register(StockLocation)
class StockLocationAdmin(admin.ModelAdmin):
    list_display = ("name", "location_type", "site", "employee", "is_active")
    list_filter = ("location_type", "is_active", "site")
    search_fields = ("name", "employee__username", "employee__first_name", "employee__last_name")
    filter_horizontal = ("warehouse_managers",)


@admin.register(StockTransferRequest)
class StockTransferRequestAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "request_type",
        "requested_by",
        "warehouse_manager",
        "warehouse",
        "status",
        "created_at",
        "reviewed_at",
    )
    list_filter = ("request_type", "status", "warehouse")
    search_fields = (
        "requested_by__username",
        "warehouse_manager__username",
        "reference",
    )
    readonly_fields = ("created_at", "reviewed_at", "approved_by", "approved_movement", "invoice_return")
    inlines = (StockTransferRequestItemInline,)


class StockTransferRequestItemInline(admin.TabularInline):
    model = StockTransferRequestItem
    extra = 0
    readonly_fields = ("product", "quantity", "invoice_item")


@admin.register(StockBalance)
class StockBalanceAdmin(admin.ModelAdmin):
    list_display = ("location", "product", "quantity", "total_cost", "updated_at")
    list_filter = ("location",)
    search_fields = ("location__name", "product__name")
    readonly_fields = ("quantity", "total_cost", "updated_at")


@admin.register(StockBatchBalance)
class StockBatchBalanceAdmin(admin.ModelAdmin):
    list_display = ("location", "batch", "quantity", "total_cost", "updated_at")
    list_filter = ("location",)
    search_fields = ("location__name", "batch__product__name", "batch__batch_number")
    readonly_fields = ("quantity", "total_cost", "updated_at")


@admin.register(StockMovement)
class StockMovementAdmin(admin.ModelAdmin):
    list_display = ("id", "movement_type", "source_location", "destination_location", "created_by", "created_at", "reference")
    list_filter = ("movement_type", "created_at")
    search_fields = ("reference", "created_by__username", "source_location__name", "destination_location__name")
    readonly_fields = tuple(field.name for field in StockMovement._meta.fields)


@admin.register(StockMovementItem)
class StockMovementItemAdmin(admin.ModelAdmin):
    list_display = ("movement", "product", "batch", "quantity", "unit_cost")
    list_filter = ("product",)
    search_fields = ("product__name", "movement__reference")
    readonly_fields = tuple(field.name for field in StockMovementItem._meta.fields)
