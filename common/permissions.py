from rest_framework.permissions import BasePermission, DjangoModelPermissions


class ModelAccessPermission(DjangoModelPermissions):
    perms_map = {
        **DjangoModelPermissions.perms_map,
        "GET": [
            "%(app_label)s.view_%(model_name)s",
        ],
        "HEAD": [
            "%(app_label)s.view_%(model_name)s",
        ],
    }


class ReadAuthenticatedWriteStaffPermission(BasePermission):
    """Allow any authenticated user to read; restrict writes to staff.

    This is a pragmatic, coarse authorization rule used by the transactional
    domains (customers/products/coupons/invoices/payments) until full role-
    based authorization is implemented in a later phase.
    """

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        if request.method in ("GET", "HEAD", "OPTIONS"):
            return True
        return request.user.is_staff or request.user.is_superuser