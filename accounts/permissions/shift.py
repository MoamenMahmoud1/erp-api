from rest_framework.permissions import BasePermission


class EmployeeShiftPermission(BasePermission):
    permission_codename = None

    def has_permission(self, request, view):
        user = getattr(request, "user", None)
        if not user or not user.is_authenticated:
            return False
        if user.is_superuser:
            return True
        codename = getattr(view, "permission_codename", None)
        return bool(codename and user.has_perm(codename))
