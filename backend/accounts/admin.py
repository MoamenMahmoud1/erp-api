from contextlib import suppress

from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.auth.admin import GroupAdmin as BaseGroupAdmin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import Group

from .models import RoleProfile

User = get_user_model()

with suppress(admin.sites.NotRegistered):
    admin.site.unregister(Group)


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

    def get_readonly_fields(self, request, obj=None):
        fields = set(super().get_readonly_fields(request, obj))
        if not request.user.is_superuser:
            fields.update({"is_superuser", "is_staff", "groups", "user_permissions"})
        return tuple(sorted(fields))

    def has_change_permission(self, request, obj=None):
        if obj is not None and obj.is_superuser and not request.user.is_superuser:
            return False
        return super().has_change_permission(request, obj)

    def has_delete_permission(self, request, obj=None):
        return bool(request.user and request.user.is_superuser)

    def get_deleted_objects(self, objs, request):
        deleted_objects, model_count, perms_needed, protected = super().get_deleted_objects(
            objs,
            request,
        )
        if request.user.is_superuser:
            from authsession.models import AuthSession

            perms_needed.discard(AuthSession._meta.verbose_name)
        return deleted_objects, model_count, perms_needed, protected


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

    def has_add_permission(self, request):
        return request.user.is_superuser

    def has_change_permission(self, request, obj=None):
        return request.user.is_superuser

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser


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

    def has_add_permission(self, request):
        return request.user.is_superuser

    def has_change_permission(self, request, obj=None):
        return request.user.is_superuser

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser
