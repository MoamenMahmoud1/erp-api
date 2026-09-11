from django.db import transaction

from accounts.models import RoleProfile
from accounts.services.employee_shift import require_open_shift
from common.exceptions import InvalidBusinessOperation
from customer_assignments.services import require_customer_assignment

from .lifecycle import load_invoice_for_update


@transaction.atomic
def delete_invoice(invoice_id, actor=None):
    invoice = load_invoice_for_update(invoice_id, actor)
    if invoice.status != invoice.Status.DRAFT:
        raise InvalidBusinessOperation("Only draft invoices can be deleted.")

    if actor is not None and RoleProfile.requires_shift_for_user(actor):
        if invoice.created_by_id != actor.pk:
            raise InvalidBusinessOperation("A representative can only delete invoices they created.")
        require_customer_assignment(customer=invoice.customer, user=actor)

    shift = require_open_shift(actor) if actor is not None else None
    if shift is not None and invoice.site_id != shift.site_id:
        raise InvalidBusinessOperation("The invoice belongs to a different site than the current shift.")
    invoice.delete()


class DeleteInvoice:
    def __call__(self, *, invoice_id, actor=None):
        return delete_invoice(invoice_id, actor)
