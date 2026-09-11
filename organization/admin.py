from django.contrib import admin

from .models import Department, Site


@admin.register(Site)
class SiteAdmin(admin.ModelAdmin):
    list_display = ("id", "code", "name", "site_type", "company", "parent", "is_active")
    list_filter = ("site_type", "is_active", "company")
    search_fields = ("code", "name", "company__name")
    list_select_related = ("company", "parent")


@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ("id", "code", "name", "company", "site", "is_active")
    list_filter = ("is_active", "company")
    search_fields = ("code", "name", "company__name", "site__name")
    list_select_related = ("company", "site")
