from decimal import Decimal

from django.db import transaction

from common.exceptions import InvalidBusinessOperation, InvalidMoney
from common.money import quantize_money
from invoices.models import Invoice
from payments.models import PaymentAllocation, PaymentRefund


class RefundError(InvalidBusinessOperation):
    pass


class RefundAmountTooLarge(RefundError):
    pass


@transaction.atomic
def refund_payment(*, transaction_id, invoice_id, amount, created_by_id, reason=""):
    amount = quantize_money(amount)
    if amount <= 0:
        raise InvalidMoney("Refund amount must be greater than zero.")

    invoice = Invoice.objects.select_for_update().get(pk=invoice_id)
    if invoice.status not in (Invoice.Status.CONFIRMED, Invoice.Status.PAID):
        raise RefundError("Only confirmed or paid invoices can be refunded.")

    allocations = list(
        PaymentAllocation.objects.filter(
            transaction_id=transaction_id,
            invoice_id=invoice_id,
        )
        .select_for_update()
        .prefetch_related("refunds")
        .order_by("created_at", "id")
    )
    if not allocations:
        raise RefundError("No matching payment allocation exists.")

    remaining = amount
    for allocation in allocations:
        refundable = allocation.refundable_amount
        if refundable <= 0:
            continue
        refund_amount = min(remaining, refundable)
        cash_refund = min(refund_amount, allocation.cash_amount)
        transfer_refund = refund_amount - cash_refund
        PaymentRefund.objects.create(
            transaction_id=transaction_id,
            invoice=invoice,
            allocation=allocation,
            cash_amount=cash_refund,
            transfer_amount=transfer_refund,
            reason=reason,
            created_by_id=created_by_id,
        )
        remaining -= refund_amount
        if remaining <= 0:
            break

    if remaining > Decimal("0"):
        raise RefundAmountTooLarge("Refund amount exceeds refundable payment amount.")

    if invoice.status == Invoice.Status.PAID and invoice.paid_amount < invoice.total:
        invoice.status = Invoice.Status.CONFIRMED
        invoice.save(update_fields=("status", "updated_at"))

    return invoice
