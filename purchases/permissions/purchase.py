from rest_framework.permissions import BasePermission


class PurchaseAccessPermission(BasePermission):
    permission_map = {
        "GET": "purchases.view_purchase",
        "POST": "purchases.add_purchase",
        "PUT": "purchases.change_purchase",
        "PATCH": "purchases.change_purchase",
        "DELETE": "purchases.delete_purchase",
    }

    async def has_permission(self, request, view):
        user = request.user

        if not user or not user.is_authenticated:
            return False

        if user.is_superuser:
            return True

        codename = getattr(view, "permission_codename", None)

        if codename:
            return await user.ahas_perm(codename)

        codename = self.permission_map.get(request.method)

        if not codename:
            return False

        return await user.ahas_perm(codename)