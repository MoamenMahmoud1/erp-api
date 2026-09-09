from rest_framework.permissions import BasePermission


class InvoicePermission(BasePermission):
    ACTION_PERMISSIONS = {
        "create": "invoices.add_invoice",
        "acreate": "invoices.add_invoice",
        "update": "invoices.change_invoice",
        "aupdate": "invoices.change_invoice",
        "partial_update": "invoices.change_invoice",
        "partial_aupdate": "invoices.change_invoice",
        "destroy": "invoices.delete_invoice",
        "adestroy": "invoices.delete_invoice",
        "confirm": "invoices.confirm_invoice",
        "cancel": "invoices.cancel_invoice",
        "apply_coupon": "invoices.apply_invoice_coupon",
        "remove_coupon": "invoices.apply_invoice_coupon",
        "returns": "invoices.return_invoice",
    }

    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated:
            return False
        if user.is_superuser:
            return True
        if request.method in ("GET", "HEAD", "OPTIONS"):
            return user.has_perm("invoices.view_invoice")
        codename = self.ACTION_PERMISSIONS.get(getattr(view, "action", None))
        return bool(codename and user.has_perm(codename))
