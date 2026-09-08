from rest_framework.permissions import BasePermission


class InventoryReadPermission(BasePermission):
    """Inventory visibility stays intentionally broad to authenticated staff/users."""

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated)


class InventoryTransferPermission(BasePermission):
    def has_permission(self, request, view):
        user = request.user
        return bool(
            user
            and user.is_authenticated
            and (user.is_superuser or user.has_perm("inventory.transfer_stock"))
        )
