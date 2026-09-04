"""Synchronous payment collection domain services."""

import hashlib
import json
from decimal import Decimal

from django.db import IntegrityError, transaction
from django.db.models import F, Sum

from common.exceptions import InvalidBusinessOperation, InvalidMoney
from common.money import quantize_money
from common.observability import log_operation
from invoices.models import Invoice
from payments.models import IdempotencyKey, PaymentAllocation, PaymentTransaction


class PaymentError(InvalidBusinessOperation):
    """Base error for payment-collection business rule violations."""


class OverpaymentError(PaymentError):
    """Raised when received money exceeds the customer's total outstanding."""


class NoConfirmableInvoicesError(PaymentError):
    """Raised when the customer has nothing confirmable to pay."""


def _request_signature(data) -> str:
    canonical = json.dumps(data, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


@transaction.atomic
def _process_collection(*, customer, cash_amount, transfer_amount, collected_by_id):
    """Atomically receive and allocate a customer payment."""
    cash = quantize_money(cash_amount)
    transfer = quantize_money(transfer_amount)

    if cash < 0 or transfer < 0:
        raise InvalidMoney("Cash and transfer amounts must not be negative.")

    total_received = quantize_money(cash + transfer)
    if total_received == 0:
        return None

    invoices = list(
        Invoice.objects.filter(
            customer=customer,
            status=Invoice.Status.CONFIRMED,
        )
        .select_for_update(of=("self",))
        .select_related("customer")
        .prefetch_related("items")
        .order_by("created_at", "id")
    )

    paid_rows = (
        PaymentAllocation.objects.filter(invoice_id__in=[inv.pk for inv in invoices])
        .values("invoice_id")
        .annotate(paid=Sum(F("cash_amount") + F("transfer_amount")))
    )
    paid_map = {
        row["invoice_id"]: quantize_money(row["paid"] or Decimal("0"))
        for row in paid_rows
    }

    info = []
    total_outstanding = Decimal("0")
    for invoice in invoices:
        total = quantize_money(invoice.total)
        paid = paid_map.get(invoice.pk, Decimal("0"))
        outstanding = quantize_money(total - paid)
        if outstanding <= 0:
            continue
        info.append((invoice, total, paid, outstanding))
        total_outstanding += outstanding

    if total_outstanding == 0:
        raise NoConfirmableInvoicesError(
            "The customer has no outstanding confirmed invoices."
        )

    if total_received > total_outstanding:
        raise OverpaymentError(
            "The received amount exceeds the outstanding balance."
        )

    payment = PaymentTransaction.objects.create(
        customer=customer,
        collected_by_id=collected_by_id,
        cash_amount=cash,
        transfer_amount=transfer,
    )

    cash_remaining = cash
    transfer_remaining = transfer
    running_paid = {invoice.pk: paid for invoice, _, paid, _ in info}

    for invoice, total, _paid, outstanding in info:
        cash_use = min(cash_remaining, outstanding)
        remaining_after_cash = outstanding - cash_use
        transfer_use = min(transfer_remaining, remaining_after_cash)

        if cash_use == 0 and transfer_use == 0:
            continue

        PaymentAllocation.objects.create(
            transaction=payment,
            invoice=invoice,
            cash_amount=cash_use,
            transfer_amount=transfer_use,
        )

        running_paid[invoice.pk] += cash_use + transfer_use
        cash_remaining -= cash_use
        transfer_remaining -= transfer_use

        if running_paid[invoice.pk] >= total:
            invoice.status = Invoice.Status.PAID
            invoice.save(update_fields=("status", "updated_at"))

        if cash_remaining == 0 and transfer_remaining == 0:
            break

    log_operation(
        "payment.collection",
        user=collected_by_id,
        customer=customer.pk,
        invoices_allocated=len(info),
    )
    return payment


class ProcessCollection:
    """Synchronous payment collection use case."""

    def __call__(self, *, customer, cash_amount, transfer_amount, collected_by_id):
        return _process_collection(
            customer=customer,
            cash_amount=cash_amount,
            transfer_amount=transfer_amount,
            collected_by_id=collected_by_id,
        )


@transaction.atomic
def _process_collection_idempotent(
    *,
    key,
    user_id,
    path,
    data,
    customer,
    cash_amount,
    transfer_amount,
):
    """Run collection with durable, transactional idempotency."""
    signature = _request_signature(data)

    existing = (
        IdempotencyKey.objects.select_for_update()
        .filter(key=key, user_id=user_id, path=path)
        .first()
    )
    if existing is not None:
        if existing.request_signature != signature:
            return "mismatch"
        return existing

    try:
        with transaction.atomic():
            record = IdempotencyKey.objects.create(
                key=key,
                user_id=user_id,
                path=path,
                request_signature=signature,
                response_status=0,
                response_body={},
            )
    except IntegrityError:
        winner = (
            IdempotencyKey.objects.select_for_update()
            .filter(key=key, user_id=user_id, path=path)
            .first()
        )
        if winner is None:
            raise InvalidBusinessOperation("Idempotency conflict — please retry.")
        if winner.request_signature != signature:
            return "mismatch"
        return winner

    payment = _process_collection(
        customer=customer,
        cash_amount=cash_amount,
        transfer_amount=transfer_amount,
        collected_by_id=user_id,
    )

    if payment is None:
        response_status = 200
        response_body = {
            "detail": "Zero-value collection is a no-op.",
            "code": "noop",
        }
    else:
        from payments.api.serializers import PaymentTransactionSerializer

        response_status = 201
        response_body = PaymentTransactionSerializer(payment).data

    record.response_status = response_status
    record.response_body = response_body
    record.save(update_fields=("response_status", "response_body"))
    return record


class ProcessCollectionIdempotent:
    """Synchronous collection use case with transactional idempotency."""

    def __call__(
        self,
        *,
        key,
        user_id,
        path,
        data,
        customer,
        cash_amount,
        transfer_amount,
    ):
        return _process_collection_idempotent(
            key=key,
            user_id=user_id,
            path=path,
            data=data,
            customer=customer,
            cash_amount=cash_amount,
            transfer_amount=transfer_amount,
        )


__all__ = (
    "NoConfirmableInvoicesError",
    "OverpaymentError",
    "PaymentError",
    "ProcessCollection",
    "ProcessCollectionIdempotent",
)
