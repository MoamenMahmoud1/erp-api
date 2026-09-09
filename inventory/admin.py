from django.contrib import admin

from .models import InventoryBatch, StockBalance, StockBatchBalance, StockLocation, StockMovement, StockMovementItem


class StockMovementItemInline(admin.TabularInline):
    model = StockMovementItem
    extra = 0
    autocomplete_fields = ("product", "batch")


@admin.register(InventoryBatch)
class InventoryBatchAdmin(admin.ModelAdmin):
    list_display = ("product", "batch_number", "manufactured_date", "expiry_date", "created_at")
    list_filter = ("expiry_date", "manufactured_date")
    search_fields = ("product__name", "batch_number")
    ordering = ("expiry_date", "product__name")
    list_select_related = ("product",)
    autocomplete_fields = ("product",)
    readonly_fields = ("created_at",)


@admin.register(StockBatchBalance)
class StockBatchBalanceAdmin(admin.ModelAdmin):
    list_display = ("location", "product", "batch_number", "quantity", "expiry_date", "total_cost", "updated_at")
    list_filter = ("location", "batch__expiry_date")
    search_fields = ("location__name", "batch__batch_number", "batch__product__name")
    ordering = ("batch__expiry_date", "location__name")
    list_select_related = ("location", "batch__product")
    autocomplete_fields = ("location", "batch")
    readonly_fields = ("updated_at",)

    @admin.display(description="Product")
    def product(self, obj):
        return obj.batch.product

    @admin.display(description="Batch")
    def batch_number(self, obj):
        return obj.batch.batch_number or obj.batch_id

    @admin.display(description="Expiry")
    def expiry_date(self, obj):
        return obj.batch.expiry_date


@admin.register(StockLocation)
class StockLocationAdmin(admin.ModelAdmin):
    list_display = ("name", "location_type", "employee", "is_active", "created_at")
    list_filter = ("location_type", "is_active")
    search_fields = ("name", "employee__username", "employee__email")
    ordering = ("name",)
    list_select_related = ("employee",)
    autocomplete_fields = ("employee",)
    readonly_fields = ("created_at",)


@admin.register(StockMovement)
class StockMovementAdmin(admin.ModelAdmin):
    list_display = ("id", "movement_type", "source_location", "destination_location", "created_by", "reference", "created_at")
    list_filter = ("movement_type", "created_at")
    search_fields = ("reference", "created_by__username")
    ordering = ("-created_at", "-id")
    list_select_related = ("source_location", "destination_location", "created_by")
    autocomplete_fields = ("source_location", "destination_location", "created_by")
    readonly_fields = ("created_at",)
    inlines = (StockMovementItemInline,)


@admin.register(StockBalance)
class StockBalanceAdmin(admin.ModelAdmin):
    list_display = ("location", "product", "quantity", "updated_at")
    list_filter = ("location",)
    search_fields = ("location__name", "product__name")
    ordering = ("location", "product")
    list_select_related = ("location", "product")
    autocomplete_fields = ("location", "product")
    readonly_fields = ("updated_at",)
