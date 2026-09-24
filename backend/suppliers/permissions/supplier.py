from rest_framework.permissions import BasePermission


class SupplierAccessPermission(BasePermission):
    permission_map = {
        "GET": "suppliers.view_supplier",
        "POST": "suppliers.add_supplier",
        "PUT": "suppliers.change_supplier",
        "PATCH": "suppliers.change_supplier",
        "DELETE": "suppliers.delete_supplier",
    }

    def has_permission(self, request, view):
        user = request.user

        if not user or not user.is_authenticated:
            return False

        if user.is_superuser:
            return True

        permission = self.permission_map.get(request.method)

        return bool(permission and user.has_perm(permission))