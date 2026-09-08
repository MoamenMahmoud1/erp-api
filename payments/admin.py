from django.contrib import admin

from unfold.admin import ModelAdmin

from .models import PaymentAllocation, PaymentTransaction


@admin.register(PaymentTransaction)
class PaymentTransactionAdmin(ModelAdmin):
    list_display = (
        "id",
        "customer",
        "cash_amount",
        "transfer_amount",
        "created_at",
    )
    list_filter = ("created_at",)
    search_fields = ("customer__name",)
    ordering = ("-created_at", "-id")
    list_select_related = ("customer",)


@admin.register(PaymentAllocation)
class PaymentAllocationAdmin(ModelAdmin):
    list_display = (
        "id",
        "transaction",
        "invoice",
        "cash_amount",
        "transfer_amount",
        "created_at",
    )
    list_filter = ("created_at",)
    search_fields = ("invoice__id", "invoice__customer__name")
    ordering = ("-created_at", "-id")
    list_select_related = ("transaction", "invoice", "invoice__customer")
