from django.contrib import admin
from django.db import transaction
from django.utils import timezone

from authsession.cache import delete_auth_session_caches
from authsession.models import AuthSession


@admin.register(AuthSession)
class RevokedStatusFilter(admin.SimpleListFilter):
    title = "Session status"
    parameter_name = "session_status"

    def lookups(self, request, model_admin):
        return (
            ("active", "Active"),
            ("revoked", "Revoked"),
            ("expired", "Expired"),
        )

    def queryset(self, request, queryset):
        now = timezone.now()
        if self.value() == "active":
            return queryset.filter(
                revoked_at__isnull=True,
                expires_at__gt=now,
            )
        if self.value() == "revoked":
            return queryset.filter(revoked_at__isnull=False)
        if self.value() == "expired":
            return queryset.filter(
                revoked_at__isnull=True,
                expires_at__lte=now,
            )
        return queryset


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
        "status",
    )
    list_filter = (
        RevokedStatusFilter,
        ("user", admin.RelatedOnlyFieldListFilter),
        "created_at",
        "expires_at",
    )
    date_hierarchy = "created_at"
    search_fields = ("user__username", "user__email", "device_name", "ip_address")
    ordering = ("-created_at",)
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
    actions = ("revoke_sessions",)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return request.user.is_superuser

    def has_delete_permission(self, request, obj=None):
        return False

    @admin.display(description="Status", ordering="revoked_at")
    def status(self, obj):
        if obj.revoked_at is not None:
            return "Revoked"
        if obj.expires_at <= timezone.now():
            return "Expired"
        return "Active"

    @admin.action(description="Revoke selected sessions")
    def revoke_sessions(self, request, queryset):
        session_ids = tuple(
            queryset.filter(revoked_at__isnull=True).values_list("pk", flat=True)
        )
        if not session_ids:
            self.message_user(
                request,
                "No active sessions were selected.",
                level="warning",
            )
            return

        revoked_at = timezone.now()
        with transaction.atomic():
            updated = AuthSession.objects.filter(
                pk__in=session_ids,
                revoked_at__isnull=True,
            ).update(revoked_at=revoked_at)
            if updated:
                transaction.on_commit(
                    lambda ids=session_ids: delete_auth_session_caches(ids)
                )

        self.message_user(
            request,
            f"Revoked {updated} session(s).",
            level="success",
        )
