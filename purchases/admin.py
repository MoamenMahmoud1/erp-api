from django.contrib import admin

from .models import Purchase, PurchaseItem, SupplierPayment


class PurchaseItemInline(admin.TabularInline):
    model = PurchaseItem
    extra = 0


@admin.register(Purchase)
class PurchaseAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "reference",
        "supplier",
        "status",
        "total_amount",
        "created_by",
        "created_at",
    )
    list_filter = ("status", "created_at")
    search_fields = ("reference", "supplier__name", "created_by__username")
    ordering = ("-created_at", "-id")
    list_select_related = ("supplier", "created_by")
    autocomplete_fields = ("supplier", "created_by")
    inlines = (PurchaseItemInline,)


@admin.register(SupplierPayment)
class SupplierPaymentAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "supplier",
        "cash_amount",
        "transfer_amount",
        "total_amount",
        "paid_by",
        "reference",
        "created_at",
    )
    list_filter = ("created_at",)
    search_fields = ("supplier__name", "paid_by__username", "reference")
    ordering = ("-created_at", "-id")
    list_select_related = ("supplier", "paid_by")
