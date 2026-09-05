from django.db import transaction

from common.exceptions import InvalidBusinessOperation
from common.money import quantize_money
from invoices.models import Invoice
from payments.models import PaymentAllocation

from .refund import refund_payment


@transaction.atomic
def refund_invoice(*, invoice_id, amount, created_by_id, reason=""):
    invoice = Invoice.objects.select_for_update().get(pk=invoice_id)
    if invoice.status not in (Invoice.Status.CONFIRMED, Invoice.Status.PAID):
        raise InvalidBusinessOperation("Only confirmed or paid invoices can be refunded.")

    amount = quantize_money(amount)
    if amount <= 0 or amount > invoice.paid_amount:
        raise InvalidBusinessOperation("Refund amount exceeds the invoice's refundable amount.")

    remaining = amount
    allocations = (
        PaymentAllocation.objects.filter(invoice=invoice)
        .select_for_update()
        .select_related("transaction")
        .prefetch_related("refunds")
        .order_by("created_at", "id")
    )
    for allocation in allocations:
        refundable = allocation.refundable_amount
        if refundable <= 0:
            continue
        chunk = min(remaining, refundable)
        refund_payment(
            transaction_id=allocation.transaction_id,
            invoice_id=invoice.pk,
            amount=chunk,
            created_by_id=created_by_id,
            reason=reason,
        )
        remaining -= chunk
        if remaining <= 0:
            break

    if remaining > 0:
        raise InvalidBusinessOperation("Refund allocation could not cover the requested amount.")
    return invoice
