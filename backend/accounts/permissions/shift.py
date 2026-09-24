from rest_framework.permissions import BasePermission


class EmployeeShiftPermission(BasePermission):
    def has_permission(self, request, view):
        user = getattr(request, "user", None)
        if not user or not user.is_authenticated:
            return False
        if user.is_superuser:
            return True
        codename = getattr(view, "permission_codename", None)
        if codename:
            return user.has_perm(codename)
        return any(
            user.has_perm(permission)
            for permission in (
                "accounts.start_employee_shift",
                "accounts.close_employee_shift",
                "accounts.view_all_employee_shifts",
            )
        )
