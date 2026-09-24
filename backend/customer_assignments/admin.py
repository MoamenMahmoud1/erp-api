from django.contrib import admin

from .models import CustomerAssignment


@admin.register(CustomerAssignment)
class CustomerAssignmentAdmin(admin.ModelAdmin):
    list_display = ("customer", "employee", "is_active", "created_at", "updated_at")
    list_filter = ("is_active",)
    search_fields = (
        "customer__name",
        "customer__phone",
        "employee__user__username",
        "employee__user__first_name",
        "employee__user__last_name",
    )
    autocomplete_fields = ("customer", "employee")
