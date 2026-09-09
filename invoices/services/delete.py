from django.db import transaction

from accounts.services.employee_shift import require_open_shift
from common.exceptions import InvalidBusinessOperation

from .lifecycle import load_invoice_for_update


@transaction.atomic
def delete_invoice(invoice_id, actor=None):
    invoice = load_invoice_for_update(invoice_id, actor)
    if invoice.status != invoice.Status.DRAFT:
        raise InvalidBusinessOperation("Only draft invoices can be deleted.")
    shift = require_open_shift(actor) if actor is not None else None
    if shift is not None and invoice.site_id != shift.site_id:
        raise InvalidBusinessOperation("The invoice belongs to a different site than the current shift.")
    invoice.delete()


class DeleteInvoice:
    def __call__(self, *, invoice_id, actor=None):
        return delete_invoice(invoice_id, actor)
