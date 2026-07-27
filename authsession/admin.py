from django.contrib import admin

from authsession.models import AuthSession


@admin.register(AuthSession)
class AuthSessionAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "user",
        "device_name",
        "ip_address",
        "created_at",
        "last_refreshed_at",
        "expires_at",
        "revoked_at",
    )
    list_filter = ("created_at", "expires_at", "revoked_at")
    search_fields = ("user__username", "user__email", "device_name", "ip_address")
    list_select_related = ("user",)
    readonly_fields = (
        "id",
        "user",
        "device_id",
        "device_name",
        "user_agent",
        "ip_address",
        "current_refresh_jti",
        "created_at",
        "last_refreshed_at",
        "expires_at",
        "revoked_at",
    )
