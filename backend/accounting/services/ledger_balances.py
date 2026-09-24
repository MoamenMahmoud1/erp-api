"""Canonical AR/AP balances derived from posted general-ledger activity."""

from decimal import Decimal

from django.db.models import Sum

from accounting.models import Account, JournalEntry, JournalLine
from accounting.services.journal import get_default_company
from invoices.models import Invoice, InvoiceReturn
from payments.models import PaymentRefund, PaymentTransaction
from purchases.models import Purchase, PurchaseReturn, SupplierPayment

ZERO = Decimal("0.00")

_CUSTOMER_SOURCES = (
    "invoice.sale",
    "invoice.return",
    "payment.collection",
    "payment.refund",
)
_SUPPLIER_SOURCES = (
    "purchase.confirmation",
    "purchase.return",
    "payment.supplier",
)


def _owner_map(source_type, source_ids):
    if not source_ids:
        return {}
    if source_type == "invoice.sale":
        return dict(Invoice.objects.filter(pk__in=source_ids).values_list("pk", "customer_id"))
    if source_type == "invoice.return":
        return dict(InvoiceReturn.objects.filter(pk__in=source_ids).values_list("pk", "invoice__customer_id"))
    if source_type == "payment.collection":
        return dict(PaymentTransaction.objects.filter(pk__in=source_ids).values_list("pk", "customer_id"))
    if source_type == "payment.refund":
        return dict(PaymentRefund.objects.filter(pk__in=source_ids).values_list("pk", "invoice__customer_id"))
    if source_type == "purchase.confirmation":
        return dict(Purchase.objects.filter(pk__in=source_ids).values_list("pk", "supplier_id"))
    if source_type == "purchase.return":
        return dict(PurchaseReturn.objects.filter(pk__in=source_ids).values_list("pk", "purchase__supplier_id"))
    if source_type == "payment.supplier":
        return dict(SupplierPayment.objects.filter(pk__in=source_ids).values_list("pk", "supplier_id"))
    return {}


def _owner_maps(source_types, entries):
    """Resolve all source-owner relationships in bounded batches."""
    ids_by_type = {}
    for entry in entries:
        source_type = entry["source_type"]
        source_id = entry["source_id"]
        if source_type in source_types and source_id is not None:
            ids_by_type.setdefault(source_type, set()).add(source_id)
    return {
        source_type: _owner_map(source_type, ids)
        for source_type, ids in ids_by_type.items()
    }


def _entry_line_totals(entry_ids, account):
    """Aggregate the relevant AR/AP line for every entry in one query."""
    if not entry_ids:
        return {}
    return {
        row["entry_id"]: row
        for row in JournalLine.objects.filter(
            entry_id__in=entry_ids,
            account=account,
        )
        .values("entry_id")
        .annotate(debit=Sum("debit"), credit=Sum("credit"))
    }


def _apply_entry_totals(*, result, entries, owner_maps, line_totals, owner_kind, reversal=False):
    for entry in entries:
        source_type = entry["source_type"]
        base_type = source_type[:-9] if reversal else source_type
        owner_id = owner_maps.get(base_type, {}).get(entry["source_id"])
        if owner_id is None:
            continue
        totals = line_totals.get(entry["id"], {})
        debit = totals.get("debit") or ZERO
        credit = totals.get("credit") or ZERO
        signed = debit - credit if owner_kind == "customer" else credit - debit
        result[owner_id] = result.get(owner_id, ZERO) + signed


def owner_ledger_balances(*, owner_kind, as_of=None, company=None):
    """Return signed canonical AR/AP balances grouped by business owner."""
    company = company or get_default_company()
    account_code = "1200" if owner_kind == "customer" else "2100"
    source_types = _CUSTOMER_SOURCES if owner_kind == "customer" else _SUPPLIER_SOURCES
    reversal_types = tuple(f"{source_type}.reversal" for source_type in source_types)
    account = Account.objects.filter(company=company, code=account_code).first()
    if account is None:
        return {}

    entries_qs = JournalEntry.objects.filter(
        company=company,
        status=JournalEntry.Status.POSTED,
        source_type__in=source_types,
    )
    if as_of is not None:
        entries_qs = entries_qs.filter(entry_date__lte=as_of)
    entries = list(entries_qs.values("id", "source_type", "source_id"))

    reversals_qs = JournalEntry.objects.filter(
        company=company,
        status=JournalEntry.Status.POSTED,
        source_type__in=reversal_types,
    )
    if as_of is not None:
        reversals_qs = reversals_qs.filter(entry_date__lte=as_of)
    reversals = list(reversals_qs.values("id", "source_type", "source_id"))

    owner_maps = _owner_maps(
        source_types,
        entries + [
            {
                **entry,
                "source_type": entry["source_type"][:-9],
            }
            for entry in reversals
        ],
    )
    line_totals = _entry_line_totals(
        [entry["id"] for entry in entries],
        account,
    )
    reversal_line_totals = _entry_line_totals(
        [entry["id"] for entry in reversals],
        account,
    )

    result = {}
    _apply_entry_totals(
        result=result,
        entries=entries,
        owner_maps=owner_maps,
        line_totals=line_totals,
        owner_kind=owner_kind,
    )
    _apply_entry_totals(
        result=result,
        entries=reversals,
        owner_maps=owner_maps,
        line_totals=reversal_line_totals,
        owner_kind=owner_kind,
        reversal=True,
    )
    return result


__all__ = ("owner_ledger_balances",)
