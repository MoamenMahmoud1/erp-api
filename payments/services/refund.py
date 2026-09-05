from django.db import transaction

from accounting.services import get_default_company, post_payment_refund
from common.exceptions import InvalidBusinessOperation, InvalidMoney
from common.money import quantize_money
from invoices.models import Invoice
from payments.models import PaymentAllocation, PaymentRefund


class RefundError(InvalidBusinessOperation):
    pass


class RefundAmountTooLarge(RefundError):
    pass


@transaction.atomic
def refund_payment(*, transaction_id, invoice_id, amount, created_by_id, reason="", actor=None):
    amount = quantize_money(amount)
    if amount <= 0:
        raise InvalidMoney("Refund amount must be greater than zero.")

    invoice_qs = Invoice.objects.visible_to(actor) if actor is not None else Invoice.objects
    invoice = invoice_qs.select_for_update().get(pk=invoice_id)
    if invoice.status not in (Invoice.Status.CONFIRMED, Invoice.Status.PAID):
        raise RefundError("Only confirmed or paid invoices can be refunded.")

    allocation = PaymentAllocation.objects.filter(transaction_id=transaction_id, invoice_id=invoice_id).select_for_update().prefetch_related("refunds").first()
    if allocation is None:
        raise RefundError("No matching payment allocation exists.")
    if amount > allocation.refundable_amount:
        raise RefundAmountTooLarge("Refund amount exceeds refundable payment amount.")

    refund = PaymentRefund.objects.create(
        transaction_id=transaction_id,
        invoice=invoice,
        allocation=allocation,
        cash_amount=min(amount, allocation.cash_amount),
        transfer_amount=amount - min(amount, allocation.cash_amount),
        reason=reason,
        created_by_id=created_by_id,
    )
    post_payment_refund(refund=refund, actor_id=created_by_id, company=get_default_company())
    return invoice
