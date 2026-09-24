from rest_framework.permissions import BasePermission


class InventoryReadPermission(BasePermission):
    """Require an explicit read permission for the requested inventory resource."""

    def has_permission(self, request, view):
        user = getattr(request, "user", None)
        if not user or not user.is_authenticated:
            return False
        if user.is_superuser:
            return True

        codename = getattr(view, "permission_codename", None)
        return bool(codename and user.has_perm(codename))


class InventoryTransferPermission(BasePermission):
    """Legacy permission kept for callers that can initiate transfer operations."""

    def has_permission(self, request, view):
        user = getattr(request, "user", None)
        return bool(
            user
            and user.is_authenticated
            and (user.is_superuser or user.has_perm("inventory.transfer_stock"))
        )


class InventoryApprovedTransferPermission(BasePermission):
    """Only warehouse approvers can execute a direct stock movement endpoint."""

    def has_permission(self, request, view):
        user = getattr(request, "user", None)
        return bool(
            user
            and user.is_authenticated
            and (user.is_superuser or user.has_perm("inventory.approve_stock_transfer"))
        )


class InventoryTransferRequestPermission(BasePermission):
    """Representatives create requests; warehouse approvers can also read them."""

    def has_permission(self, request, view):
        user = getattr(request, "user", None)
        if not user or not user.is_authenticated:
            return False
        if user.is_superuser:
            return True
        if request.method in ("GET", "HEAD", "OPTIONS"):
            return user.has_perm("inventory.transfer_stock") or user.has_perm("inventory.approve_stock_transfer")
        return user.has_perm("inventory.transfer_stock")
