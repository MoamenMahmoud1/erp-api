from django.contrib import admin

from unfold.admin import ModelAdmin

from .models import Company, Department, Site


@admin.register(Company)
class CompanyAdmin(ModelAdmin):
    list_display = (
        "name",
        "registration_number",
        "tax_number",
        "email",
        "phone",
        "updated_at",
    )
    search_fields = (
        "name",
        "legal_name",
        "registration_number",
        "tax_number",
    )
    ordering = ("name",)
    readonly_fields = ("singleton_marker", "created_at", "updated_at")

    def has_add_permission(self, request):
        return not Company.objects.exists() and super().has_add_permission(request)

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Site)
class SiteAdmin(ModelAdmin):
    list_display = (
        "code",
        "name",
        "site_type",
        "company",
        "parent",
        "is_active",
        "updated_at",
    )
    list_filter = ("site_type", "is_active")
    search_fields = ("code", "name", "company__name", "city")
    ordering = ("company", "code")
    list_select_related = ("company", "parent")
    autocomplete_fields = ("company", "parent")
    readonly_fields = ("created_at", "updated_at")


@admin.register(Department)
class DepartmentAdmin(ModelAdmin):
    list_display = (
        "code",
        "name",
        "company",
        "site",
        "is_active",
        "updated_at",
    )
    list_filter = ("is_active", "company", "site")
    search_fields = ("code", "name", "company__name")
    ordering = ("company", "code")
    list_select_related = ("company", "site")
    autocomplete_fields = ("company", "site")
    readonly_fields = ("created_at", "updated_at")
