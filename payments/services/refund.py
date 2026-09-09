from django.db import transaction

from accounts.services.employee_shift import employee_for_user, require_open_shift
from accounting.services import get_default_company, post_payment_refund
from auditlog.services import record_event
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

    shift = require_open_shift(actor) if actor is not None else None
    employee = employee_for_user(actor) if actor is not None else None
    site_id = shift.site_id if shift else (employee.work_site_id if employee else invoice.site_id)
    if shift is not None and invoice.site_id != shift.site_id:
        raise RefundError("The invoice belongs to a different site than the current shift.")

    allocation = PaymentAllocation.objects.filter(transaction_id=transaction_id, invoice_id=invoice_id).select_for_update().prefetch_related("refunds").first()
    if allocation is None:
        raise RefundError("No matching payment allocation exists.")
    if amount > allocation.refundable_amount:
        raise RefundAmountTooLarge("Refund amount exceeds refundable payment amount.")

    refund = PaymentRefund.objects.create(
        transaction_id=transaction_id,
        invoice=invoice,
        allocation=allocation,
        site_id=site_id,
        shift_id=shift.pk if shift else None,
        cash_amount=min(amount, allocation.cash_amount),
        transfer_amount=amount - min(amount, allocation.cash_amount),
        reason=reason,
        created_by_id=created_by_id,
    )
    post_payment_refund(refund=refund, actor_id=created_by_id, company=get_default_company())
    record_event(
        action="payment.refund",
        entity_type="PaymentRefund",
        entity_id=refund.pk,
        actor_id=created_by_id,
        metadata={"invoice_id": invoice.pk, "transaction_id": transaction_id, "site_id": site_id, "shift_id": refund.shift_id, "reason": reason},
    )
    return invoice
