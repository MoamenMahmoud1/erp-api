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
    inlines = (InvoiceItemInline,)
