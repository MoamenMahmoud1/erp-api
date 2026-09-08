from django.contrib import admin

from unfold.admin import ModelAdmin

from .models import Customer


@admin.register(Customer)
class CustomerAdmin(ModelAdmin):
    list_display = ("name", "phone", "created_at")
    search_fields = ("name", "phone")
    ordering = ("name",)
