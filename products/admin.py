from django.contrib import admin

from unfold.admin import ModelAdmin

from .models import CartonPricing, Product


@admin.register(Product)
class ProductAdmin(ModelAdmin):
    list_display = ("name", "category", "purchase_price", "selling_price", "created_at")
    search_fields = ("name", "category")
    list_filter = ("category",)
    ordering = ("name",)


@admin.register(CartonPricing)
class CartonPricingAdmin(ModelAdmin):
    list_display = ("name", "units_per_carton", "carton_price")
    search_fields = ("name",)
    ordering = ("name",)
