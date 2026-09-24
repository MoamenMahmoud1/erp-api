from decimal import Decimal

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

    try:
        payment = (
            queryset.select_for_update()
            .select_related("customer")
            .prefetch_related("allocations__invoice")
            .get(pk=transaction_id)
        )
    except PaymentTransaction.DoesNotExist as exc:
        raise TransferApprovalError("The payment transaction was not found.") from exc

    if payment.transfer_amount <= 0:
        raise TransferApprovalError(
            "Only payments containing a bank transfer can be approved."
        )

    if payment.transfer_accepted:
        payment._transfer_approved = True
        return payment

    allocations = list(payment.allocations.all())
    transfer_by_invoice = {}
    for allocation in allocations:
        transfer_by_invoice.setdefault(allocation.invoice_id, Decimal("0"))
        transfer_by_invoice[allocation.invoice_id] += allocation.transfer_amount

    if not allocations or sum(transfer_by_invoice.values(), Decimal("0")) != payment.transfer_amount:
        raise TransferApprovalError(
            "The payment transfer allocations are inconsistent."
        )

    invoices = list(
        Invoice.objects.select_for_update()
        .filter(pk__in=transfer_by_invoice)
        .order_by("pk")
    )
    if len(invoices) != len(transfer_by_invoice):
        raise TransferApprovalError("A transfer allocation references a missing invoice.")

    for invoice in invoices:
        transfer_amount = transfer_by_invoice[invoice.pk]
        if invoice.status not in (Invoice.Status.CONFIRMED, Invoice.Status.PAID):
            raise TransferApprovalError(
                "Only confirmed invoices can accept a bank transfer."
            )
        if invoice.net_paid_amount + transfer_amount > invoice.total:
            raise TransferApprovalError(
                f"Approving this transfer would overpay invoice #{invoice.pk}."
            )

    post_customer_transfer_approval(
        payment=payment,
        actor_id=actor_id,
        company=get_default_company(),
    )
    payment._transfer_approved = True

    invoice_ids = [invoice.pk for invoice in invoices]
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
