from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.auth.admin import GroupAdmin as BaseGroupAdmin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import Group

from .models import Employee, RoleProfile

User = get_user_model()

try:
    admin.site.unregister(Group)
except admin.sites.NotRegistered:
    pass


@admin.register(User)
class CustomUserAdmin(BaseUserAdmin):
    list_display = (
        "id",
        "username",
        "email",
        "phone_number",
        "is_verified",
        "is_active",
        "is_staff",
    )

    search_fields = (
        "username",
        "email",
        "first_name",
        "last_name",
        "phone_number",
    )

    list_filter = (
        "is_active",
        "is_staff",
        "is_superuser",
        "is_verified",
        "groups",
    )

    ordering = ("-date_joined",)

    fieldsets = BaseUserAdmin.fieldsets + (
        (
            "Additional Information",
            {
                "fields": (
                    "phone_number",
                    "photo",
                    "is_verified",
                    "password_changed_at",
                    "updated_at",
                )
            },
        ),
    )

    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        (
            "Additional Information",
            {
                "classes": ("wide",),
                "fields": (
                    "email",
                    "phone_number",
                    "photo",
                    "is_verified",
                ),
            },
        ),
    )

    readonly_fields = ("updated_at", "password_changed_at")


@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "manager", "work_site", "department")
    search_fields = (
        "user__username",
        "user__email",
        "user__first_name",
        "user__last_name",
    )
    list_filter = ("work_site", "department")
    list_select_related = ("user", "manager", "work_site", "department")
    autocomplete_fields = ("user", "manager", "work_site", "department")


class RoleProfileInline(admin.StackedInline):
    model = RoleProfile
    extra = 1
    max_num = 1
    fields = ("name", "level", "scope", "requires_shift", "description")


@admin.register(Group)
class GroupAdmin(BaseGroupAdmin):
    search_fields = ("name",)
    ordering = ("name",)
    inlines = (RoleProfileInline,)


@admin.register(RoleProfile)
class RoleProfileAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "group",
        "level",
        "scope",
        "requires_shift",
        "updated_at",
    )
    search_fields = ("name", "group__name", "description")
    list_filter = ("scope", "requires_shift")
    ordering = ("name", "-level", "group__name")
    list_select_related = ("group",)
    autocomplete_fields = ("group",)
    readonly_fields = ("created_at", "updated_at")
