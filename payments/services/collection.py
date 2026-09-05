from decimal import Decimal

from django.db import transaction
from django.db.models import F, Sum

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


def collect(*, customer, cash_amount, transfer_amount, collected_by_id):
    """Receive money and allocate it oldest-invoice-first."""
    cash = quantize_money(cash_amount)
    transfer = quantize_money(transfer_amount)
    if cash < 0 or transfer < 0:
        raise InvalidMoney("Cash and transfer amounts must not be negative.")

    total_received = quantize_money(cash + transfer)
    if total_received == 0:
        return None

    with transaction.atomic():
        invoices = list(
            Invoice.objects.filter(customer=customer, status=Invoice.Status.CONFIRMED)
            .select_for_update(of=("self",))
            .prefetch_related("items")
            .order_by("created_at", "id")
        )
        invoice_ids = [invoice.pk for invoice in invoices]
        paid_map = {
            row["invoice_id"]: quantize_money(row["paid"] or Decimal("0"))
            for row in PaymentAllocation.objects.filter(invoice_id__in=invoice_ids)
            .values("invoice_id")
            .annotate(paid=Sum(F("cash_amount") + F("transfer_amount")))
        }

        outstanding = []
        total_outstanding = Decimal("0")
        for invoice in invoices:
            paid = paid_map.get(invoice.pk, Decimal("0"))
            due = quantize_money(invoice.total - paid)
            if due > 0:
                outstanding.append((invoice, due))
                total_outstanding += due

        if not outstanding:
            raise NoConfirmableInvoicesError("The customer has no outstanding confirmed invoices.")
        if total_received > total_outstanding:
            raise OverpaymentError("The received amount exceeds the outstanding balance.")

        payment = PaymentTransaction.objects.create(
            customer=customer,
            collected_by_id=collected_by_id,
            cash_amount=cash,
            transfer_amount=transfer,
        )
        cash_remaining, transfer_remaining = cash, transfer

        for invoice, due in outstanding:
            cash_use = min(cash_remaining, due)
            transfer_use = min(transfer_remaining, due - cash_use)
            if cash_use == 0 and transfer_use == 0:
                break

            PaymentAllocation.objects.create(
                transaction=payment,
                invoice=invoice,
                cash_amount=cash_use,
                transfer_amount=transfer_use,
            )
            cash_remaining -= cash_use
            transfer_remaining -= transfer_use

            if invoice.paid_amount >= invoice.total:
                invoice.status = Invoice.Status.PAID
                invoice.save(update_fields=("status", "updated_at"))

            if cash_remaining == 0 and transfer_remaining == 0:
                break

        log_operation(
            "payment.collection",
            user=collected_by_id,
            customer=customer.pk,
            invoices_allocated=len(outstanding),
        )
        return payment
