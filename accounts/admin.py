from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.auth.admin import UserAdmin
from django.utils.html import format_html
from django.urls import reverse

from .models import Employee, Role

User = get_user_model()


@admin.register(User)
class CustomUserAdmin(UserAdmin):
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

    fieldsets = UserAdmin.fieldsets + (
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

    add_fieldsets = UserAdmin.add_fieldsets + (
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
    list_display = (
        "id",
        "user_link",
        "manager",
        "created_at",
        "updated_at",
    )
    @admin.display(description="User", ordering="user__username")
    def user_link(self, obj):
        url = reverse(
            "admin:accounts_customusermodel_change",
            args=[obj.user_id],
        )
        return format_html('<a href="{}">{}</a>', url, obj.user)

    search_fields = (
        "user__username",
        "user__email",
        "user__first_name",
        "user__last_name",
    )

    list_filter = (
        "created_at",
    )

    ordering = ("-created_at",)

    list_select_related = (
        "user",
        "manager",
        "manager__user",
    )

    autocomplete_fields = (
        "user",
        "manager",
    )

    readonly_fields = (
        "created_at",
        "updated_at",
    )


@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "code",
        "group",
        "level",
        "is_system",
        "updated_at",
    )
    search_fields = (
        "code",
        "group__name",
    )
    list_filter = (
        "is_system",
    )
    ordering = (
        "-level",
        "code",
    )
    readonly_fields = (
        "created_at",
        "updated_at",
    )
