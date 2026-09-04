"""
Payment collection domain.

``ProcessCollection`` is the single business operation for receiving money from
a customer and allocating it to their confirmed invoices (oldest first, cash
before transfer). The backend owns the allocation entirely — a client only
reports ``cash_amount`` and ``transfer_amount``.

The whole operation (transaction + allocations + PAID transitions) runs inside
one synchronous ``transaction.atomic()`` block that locks every candidate invoice
with ``select_for_update()``, so two concurrent collections can never allocate
the same outstanding balance twice.

Idempotency is enforced transactionally: the idempotency row is created inside
the same transaction as the financial operation, before the business logic
executes.  A unique constraint on ``(key, user, path)`` guarantees that only one
request can claim a given key.  Concurrent duplicates block on
``select_for_update()`` until the first transaction commits, then return the
stored response.  If the first transaction rolls back, the duplicate is free to
claim the key and retry.
"""

import hashlib
import json
from decimal import Decimal

from asgiref.sync import sync_to_async
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
    """Canonical SHA-256 hash of the collection request body."""
    canonical = json.dumps(data, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _process_collection_sync(*, customer, cash_amount, transfer_amount, collected_by_id):
    """Synchronous, atomic collection operation.

    ``collected_by_id`` is the authenticated user's primary key — passed
    explicitly rather than derived from a dynamic attribute.
    """
    cash = quantize_money(cash_amount)
    transfer = quantize_money(transfer_amount)

    if cash < 0 or transfer < 0:
        raise InvalidMoney("Cash and transfer amounts must not be negative.")

    total_received = quantize_money(cash + transfer)

    # A zero-value collection is a documented no-op: nothing is persisted.
    if total_received == 0:
        return None

    with transaction.atomic():
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

        # Aggregate paid totals in a single query — avoids N+1.
        paid_rows = (
            PaymentAllocation.objects.filter(
                invoice_id__in=[inv.pk for inv in invoices],
            )
            .values("invoice_id")
            .annotate(paid=Sum(F("cash_amount") + F("transfer_amount")))
        )
        paid_map = {
            row["invoice_id"]: quantize_money(row["paid"] or Decimal("0"))
            for row in paid_rows
        }

        # Capture authoritative outstanding per invoice before allocating.
        info = []  # (invoice, total, paid, outstanding)
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
            if outstanding <= 0:
                continue

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

            # CONFIRMED -> PAID when cumulative allocations reach the total.
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
    """Async facade over the synchronous, atomic collection operation."""

    async def __call__(self, *, customer, cash_amount, transfer_amount, collected_by_id):
        return await sync_to_async(
            _process_collection_sync,
            thread_sensitive=True,
        )(
            customer=customer,
            cash_amount=cash_amount,
            transfer_amount=transfer_amount,
            collected_by_id=collected_by_id,
        )


def _process_collection_idempotent_sync(
    *,
    key,
    user_id,
    path,
    data,
    customer,
    cash_amount,
    transfer_amount,
):
    """Transactional idempotency wrapper around ``_process_collection_sync``.

    The idempotency row is created inside the same transaction as the financial
    operation, *before* the business logic runs.  The unique constraint on
    ``(key, user, path)`` guarantees that only one request can claim a key.
    Concurrent duplicates either block on ``select_for_update()`` (if the row
    already exists) or race to insert; the loser catches ``IntegrityError`` and
    retries within the same transaction to read the winner's stored response.

    Returns:
        IdempotencyKey: stored record (either pre-existing or newly created).
        "mismatch": if the key exists but the request body differs.
    Raises:
        OverpaymentError, NoConfirmableInvoicesError, InvalidMoney,
        InvalidBusinessOperation: if the business operation fails.  The
        idempotency row is rolled back, so a retry can re-execute.
    """
    signature = _request_signature(data)

    with transaction.atomic():
        # Lock the idempotency row if it exists — blocks concurrent duplicates.
        existing = (
            IdempotencyKey.objects.select_for_update()
            .filter(
                key=key,
                user_id=user_id,
                path=path,
            )
            .first()
        )

        if existing is not None:
            if existing.request_signature != signature:
                return "mismatch"
            return existing

        # Claim the key BEFORE executing the business operation.
        # Two concurrent requests can both reach this point because
        # ``select_for_update()`` cannot lock a row that doesn't exist yet.
        # The unique constraint catches the race: one INSERT succeeds, the
        # other raises IntegrityError.  We retry to read the winner's record.
        try:
            # Nested atomic block = SAVEPOINT.  If we lose the insert race the
            # IntegrityError only rolls back to the savepoint, leaving the
            # outer transaction usable for the recovery read below.
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
            # Lost the insert race — the winner's row is now visible.  Re-read
            # it under lock to get a consistent view of the stored response.
            winner = (
                IdempotencyKey.objects.select_for_update()
                .filter(
                    key=key,
                    user_id=user_id,
                    path=path,
                )
                .first()
            )
            if winner is None:
                # Extremely unlikely: winner rolled back.  Let the caller retry.
                raise InvalidBusinessOperation(
                    "Idempotency conflict — please retry."
                )
            if winner.request_signature != signature:
                return "mismatch"
            return winner

        # Execute the business operation.  If it fails, the entire
        # transaction rolls back (including the idempotency row), so a
        # retry can re-execute safely.
        payment = _process_collection_sync(
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

            response_serializer = PaymentTransactionSerializer(payment)
            response_status = 201
            response_body = response_serializer.data

        record.response_status = response_status
        record.response_body = response_body
        record.save(update_fields=("response_status", "response_body"))

        return record


class ProcessCollectionIdempotent:
    """Async facade that wraps the collection with transactional idempotency."""

    async def __call__(
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
        return await sync_to_async(
            _process_collection_idempotent_sync,
            thread_sensitive=True,
        )(
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