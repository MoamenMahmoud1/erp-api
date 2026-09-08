from django.contrib import admin

from unfold.admin import ModelAdmin

from .models import StockBalance, StockLocation, StockMovement, StockMovementItem


class StockMovementItemInline(admin.TabularInline):
    model = StockMovementItem
    extra = 0


@admin.register(StockLocation)
class StockLocationAdmin(ModelAdmin):
    list_display = ("name", "location_type", "employee", "is_active", "created_at")
    list_filter = ("location_type", "is_active")
    search_fields = ("name", "employee__username", "employee__email")
    ordering = ("name",)
    list_select_related = ("employee",)
    autocomplete_fields = ("employee",)
    readonly_fields = ("created_at",)


@admin.register(StockMovement)
class StockMovementAdmin(ModelAdmin):
    list_display = (
        "id",
        "movement_type",
        "source_location",
        "destination_location",
        "created_by",
        "reference",
        "created_at",
    )
    list_filter = ("movement_type", "created_at")
    search_fields = ("reference", "created_by__username")
    ordering = ("-created_at", "-id")
    list_select_related = ("source_location", "destination_location", "created_by")
    autocomplete_fields = ("source_location", "destination_location", "created_by")
    readonly_fields = ("created_at",)
    inlines = (StockMovementItemInline,)


@admin.register(StockBalance)
class StockBalanceAdmin(ModelAdmin):
    list_display = ("location", "product", "quantity", "updated_at")
    list_filter = ("location",)
    search_fields = ("location__name", "product__name")
    ordering = ("location", "product")
    list_select_related = ("location", "product")
    autocomplete_fields = ("location", "product")
    readonly_fields = ("updated_at",)

