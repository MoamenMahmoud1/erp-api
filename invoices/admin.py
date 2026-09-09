from django.contrib import admin

from .models import Invoice, InvoiceItem


class InvoiceItemInline(admin.TabularInline):
    model = InvoiceItem
    extra = 0


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "customer",
        "created_by",
        "status",
        "total",
        "created_at",
    )
    list_filter = ("status", "created_at")
    search_fields = ("customer__name", "created_by__username")
    ordering = ("-created_at", "-id")
    list_select_related = ("customer", "created_by")
    autocomplete_fields = ("customer", "created_by")
    inlines = (InvoiceItemInline,)
