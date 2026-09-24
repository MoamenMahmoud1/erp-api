from rest_framework.permissions import BasePermission, DjangoModelPermissions


class AccountingModelPermission(DjangoModelPermissions):
    """Model permissions plus explicit requirements for sensitive actions."""

    perms_map = {
        **DjangoModelPermissions.perms_map,
        "GET": ["%(app_label)s.view_%(model_name)s"],
        "HEAD": ["%(app_label)s.view_%(model_name)s"],
    }

    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated:
            return False
        if user.is_superuser:
            return True

        action_permission = getattr(view, "permission_codename", None)
        if action_permission and request.method not in {"GET", "HEAD", "OPTIONS"}:
            return user.has_perm(action_permission)

        write_permission = getattr(view, "write_permission_codename", None)
        if write_permission and request.method not in {"GET", "HEAD", "OPTIONS"}:
            return user.has_perm(write_permission)

        return super().has_permission(request, view)


class AccountingReportPermission(BasePermission):
    """Permission required for financial and management reporting endpoints."""

    def has_permission(self, request, view):
        user = request.user
        return bool(
            user
            and user.is_authenticated
            and (user.is_superuser or user.has_perm("accounting.view_financial_reports"))
        )
