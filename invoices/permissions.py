"""Business permissions for invoice operations.

Staff/superuser remains a broad fallback (backwards compatible with the earlier
coarse model), but fine-grained non-staff roles can now be granted the specific
``invoices.confirm_invoice`` / ``invoices.cancel_invoice`` /
``invoices.apply_invoice_coupon`` permissions and act through the API without
being staff.
"""

from rest_framework.permissions import BasePermission


class InvoicePermission(BasePermission):
    """Read for any authenticated user; writes require a business permission.

    Mapping of view actions to the Django permission codename they require.
    """

    ACTION_PERMISSIONS = {
        "create": "invoices.add_invoice",
        "acreate": "invoices.add_invoice",
        "confirm": "invoices.confirm_invoice",
        "cancel": "invoices.cancel_invoice",
        "apply_coupon": "invoices.apply_invoice_coupon",
    }

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False

        if request.method in ("GET", "HEAD", "OPTIONS"):
            return True

        # Broad admin fallback retained for backwards compatibility. Business
        # permissions below are the primary, granular authorization mechanism.
        if request.user.is_staff or request.user.is_superuser:
            return True

        codename = self.ACTION_PERMISSIONS.get(getattr(view, "action", None))
        if not codename:
            return False

        return request.user.has_perm(codename)