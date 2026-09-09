from django.contrib import admin

from .models import PaymentAllocation, PaymentTransaction


@admin.register(PaymentTransaction)
class PaymentTransactionAdmin(admin.ModelAdmin):
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
class PaymentAllocationAdmin(admin.ModelAdmin):
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
