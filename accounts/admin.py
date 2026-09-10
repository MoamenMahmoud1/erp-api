from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.auth.admin import GroupAdmin as BaseGroupAdmin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import Group

from .models import Role

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
        "role_display",
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
                    "role_display",
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

    readonly_fields = (
        "role_display",
        "updated_at",
        "password_changed_at",
    )

    def get_queryset(self, request):
        return super().get_queryset(request).prefetch_related("groups__role_profile")

    @admin.display(description="Role")
    def role_display(self, obj):
        if obj.is_superuser:
            return "Superuser"

        roles = []
        for group in obj.groups.all():
            role = getattr(group, "role_profile", None)
            if role is not None:
                roles.append(role)

        role = max(roles, key=lambda item: item.level, default=None)
        return str(role) if role else "—"


@admin.register(Group)
class GroupAdmin(BaseGroupAdmin):
    search_fields = ("name",)
    ordering = ("name",)


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
    list_select_related = ("group",)
    autocomplete_fields = ("group",)
    readonly_fields = (
        "created_at",
        "updated_at",
    )
