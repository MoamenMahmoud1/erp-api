from django.db import transaction

from accounting.services import get_default_company, post_customer_transfer_approval
from auditlog.services import record_event
from common.exceptions import InvalidBusinessOperation
from invoices.models import Invoice
from payments.models import PaymentTransaction


class TransferApprovalError(InvalidBusinessOperation):
    pass


@transaction.atomic
def approve_bank_transfer(*, transaction_id, actor_id, actor=None):
    queryset = PaymentTransaction.objects
    if actor is not None:
        queryset = queryset.visible_to(actor)

    payment = (
        queryset.select_for_update()
        .select_related("customer")
        .prefetch_related("allocations__invoice")
        .get(pk=transaction_id)
    )

    if payment.transfer_amount <= 0:
        raise TransferApprovalError(
            "Only payments containing a bank transfer can be approved."
        )

    post_customer_transfer_approval(
        payment=payment,
        actor_id=actor_id,
        company=get_default_company(),
    )
    payment._transfer_approved = True

    invoice_ids = list(
        payment.allocations.values_list("invoice_id", flat=True)
    )
    invoices = Invoice.objects.select_for_update().filter(pk__in=invoice_ids)
    for invoice in invoices:
        if (
            invoice.status == Invoice.Status.CONFIRMED
            and invoice.net_paid_amount >= invoice.total
        ):
            invoice.status = Invoice.Status.PAID
            invoice.save(update_fields=("status", "updated_at"))

    record_event(
        action="payment.transfer.approved",
        entity_type="PaymentTransaction",
        entity_id=payment.pk,
        actor_id=actor_id,
        metadata={
            "customer_id": payment.customer_id,
            "transfer_amount": str(payment.transfer_amount),
            "invoice_ids": invoice_ids,
        },
    )
    return payment
