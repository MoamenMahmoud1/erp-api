from django.db import transaction

from common.exceptions import InvalidBusinessOperation

from .lifecycle import load_invoice_for_update


@transaction.atomic
def delete_invoice(invoice_id, actor=None):
    invoice = load_invoice_for_update(invoice_id, actor)
    if invoice.status != invoice.Status.DRAFT:
        raise InvalidBusinessOperation("Only draft invoices can be deleted.")
    invoice.delete()


class DeleteInvoice:
    def __call__(self, *, invoice_id, actor=None):
        return delete_invoice(invoice_id, actor)
