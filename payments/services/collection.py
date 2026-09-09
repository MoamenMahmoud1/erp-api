from decimal import Decimal

from django.db import transaction

from accounts.services.employee_shift import operation_context
from accounting.services import get_default_company, post_customer_collection
from auditlog.services import record_event
from common.exceptions import InvalidBusinessOperation, InvalidMoney
from common.money import quantize_money
from common.observability import log_operation
from invoices.models import Invoice
from payments.models import PaymentAllocation, PaymentTransaction


class PaymentError(InvalidBusinessOperation):
    pass


class OverpaymentError(PaymentError):
    pass


class NoConfirmableInvoicesError(PaymentError):
    pass


@transaction.atomic
def collect(*, customer, cash_amount, transfer_amount, collected_by_id, actor=None):
    cash = quantize_money(cash_amount)
    transfer = quantize_money(transfer_amount)
    if cash < 0 or transfer < 0:
        raise InvalidMoney("Cash and transfer amounts must not be negative.")

    total_received = quantize_money(cash + transfer)
    if total_received == 0:
        return None

    shift = None
    site = None
    if actor is not None:
        _employee, site, shift = operation_context(actor)
    site_id = site.pk if site else None

    invoices = Invoice.objects.filter(customer=customer, status=Invoice.Status.CONFIRMED)
    if actor is not None:
        invoices = invoices.visible_to(actor)
    invoices = list(
        invoices.select_for_update(of=("self",))
        .prefetch_related("items", "payment_allocations", "payment_refunds")
        .order_by("created_at", "id")
    )

    outstanding = []
    total_outstanding = Decimal("0")
    for invoice in invoices:
        due = quantize_money(invoice.total - invoice.paid_amount)
        if due > 0:
            outstanding.append((invoice, due))
            total_outstanding += due

    if not outstanding:
        raise NoConfirmableInvoicesError("The customer has no outstanding confirmed invoices.")
    if total_received > total_outstanding:
        raise OverpaymentError("The received amount exceeds the outstanding balance.")

    payment = PaymentTransaction.objects.create(
        customer=customer,
        site_id=site_id,
        shift_id=shift.pk if shift else None,
        collected_by_id=collected_by_id,
        cash_amount=cash,
        transfer_amount=transfer,
    )
    cash_remaining, transfer_remaining = cash, transfer

    allocated_invoices = 0
    for invoice, due in outstanding:
        cash_use = min(cash_remaining, due)
        transfer_use = min(transfer_remaining, due - cash_use)
        if cash_use == 0 and transfer_use == 0:
            break

        allocation = PaymentAllocation.objects.create(
            transaction=payment,
            invoice=invoice,
            cash_amount=cash_use,
            transfer_amount=transfer_use,
        )
        allocated_invoices += 1
        cash_remaining -= cash_use
        transfer_remaining -= transfer_use

        new_paid = quantize_money(invoice.paid_amount + allocation.total_amount)
        if new_paid >= invoice.total:
            invoice.status = Invoice.Status.PAID
            invoice.save(update_fields=("status", "updated_at"))

        if cash_remaining == 0 and transfer_remaining == 0:
            break

    post_customer_collection(payment=payment, actor_id=collected_by_id, company=get_default_company())
    log_operation("payment.collection", user=collected_by_id, customer=customer.pk, invoices_allocated=allocated_invoices)
    record_event(
        action="payment.collection",
        entity_type="PaymentTransaction",
        entity_id=payment.pk,
        actor_id=collected_by_id,
        metadata={"customer_id": customer.pk, "site_id": site_id, "shift_id": payment.shift_id, "invoices_allocated": allocated_invoices},
    )
    return payment
