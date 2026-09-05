from django.db import transaction

from common.exceptions import InvalidBusinessOperation
from invoices.models import Invoice


@transaction.atomic
def delete_invoice(invoice_id):
    invoice = Invoice.objects.select_for_update().get(pk=invoice_id)
    if invoice.status != Invoice.Status.DRAFT:
        raise InvalidBusinessOperation("Only draft invoices can be deleted.")
    invoice.delete()


class DeleteInvoice:
    def __call__(self, *, invoice_id):
        return delete_invoice(invoice_id)
