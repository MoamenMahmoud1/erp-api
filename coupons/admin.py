from django.contrib import admin

from unfold.admin import ModelAdmin

from coupons.models import Coupon


@admin.register(Coupon)
class CouponAdmin(ModelAdmin):
    list_display = (
        "code",
        "discount_type",
        "discount_value",
        "is_active",
        "valid_from",
        "valid_until",
    )
    list_filter = ("discount_type", "is_active")
    search_fields = ("code",)
    ordering = ("code",)
