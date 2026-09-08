from rest_framework.permissions import BasePermission


class InventoryReadPermission(BasePermission):
    """Require an explicit read permission for the requested inventory resource."""

    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated:
            return False
        if user.is_superuser:
            return True

        codename = getattr(view, "permission_codename", None)
        return bool(codename and user.has_perm(codename))


class InventoryTransferPermission(BasePermission):
    def has_permission(self, request, view):
        user = request.user
        return bool(
            user
            and user.is_authenticated
            and (user.is_superuser or user.has_perm("inventory.transfer_stock"))
        )
