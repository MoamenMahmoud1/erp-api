from rest_framework.permissions import BasePermission

from common.services.mutation_authorization import MutationAuthorizationService


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
        "returns": "inventory.approve_stock_transfer",
        "representative_sale": "invoices.add_invoice",
    }

    APPROVAL_ACTIONS = {
        "update": "update",
        "aupdate": "update",
        "partial_update": "update",
        "partial_aupdate": "update",
        "destroy": "delete",
        "adestroy": "delete",
    }

    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated:
            return False
        if user.is_superuser:
            return True
        if request.method in ("GET", "HEAD", "OPTIONS"):
            return user.has_perm("invoices.view_invoice")

        view_action = getattr(view, "action", None)
        direct_permission = self.ACTION_PERMISSIONS.get(view_action)
        if not direct_permission:
            return False

        approval_action = self.APPROVAL_ACTIONS.get(view_action)
        if approval_action is None:
            return user.has_perm(direct_permission)

        decision = MutationAuthorizationService.decide(
            actor=user,
            resource="invoice",
            action=approval_action,
            direct_permission=direct_permission,
        )
        return decision.decision.value != "denied"
