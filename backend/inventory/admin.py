from django.contrib import admin

from inventory.models import (
    StockMovementItem,
    StockTransferRequest,
    StockTransferRequestItem,
)


class StockTransferRequestItemInline(admin.TabularInline):
    model = StockTransferRequestItem
    extra = 0
    readonly_fields = ("product", "quantity", "invoice_item")


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


@admin.register(StockMovementItem)
class StockMovementItemAdmin(admin.ModelAdmin):
    list_display = ("movement", "product", "batch", "quantity", "unit_cost")
    list_filter = ("product",)
    search_fields = ("product__name", "movement__reference")
    readonly_fields = tuple(field.name for field in StockMovementItem._meta.fields)
