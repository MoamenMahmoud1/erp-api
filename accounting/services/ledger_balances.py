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


def owner_ledger_balances(*, owner_kind, as_of=None, company=None):
    """Return signed canonical AR/AP balances grouped by business owner."""
    company = company or get_default_company()
    account_code = "1200" if owner_kind == "customer" else "2100"
    source_types = _CUSTOMER_SOURCES if owner_kind == "customer" else _SUPPLIER_SOURCES
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
    ids_by_type = {}
    for entry in entries:
        ids_by_type.setdefault(entry["source_type"], set()).add(entry["source_id"])
    owner_maps = {
        source_type: _owner_map(source_type, ids)
        for source_type, ids in ids_by_type.items()
    }

    result = {}
    for entry in entries:
        owner_id = owner_maps.get(entry["source_type"], {}).get(entry["source_id"])
        if owner_id is None:
            continue
        totals = JournalLine.objects.filter(
            entry_id=entry["id"],
            account=account,
        ).aggregate(debit=Sum("debit"), credit=Sum("credit"))
        debit = totals["debit"] or ZERO
        credit = totals["credit"] or ZERO
        signed = debit - credit if owner_kind == "customer" else credit - debit
        result[owner_id] = result.get(owner_id, ZERO) + signed

    reversal_types = tuple(f"{source_type}.reversal" for source_type in source_types)
    reversals_qs = JournalEntry.objects.filter(
        company=company,
        status=JournalEntry.Status.POSTED,
        source_type__in=reversal_types,
    )
    if as_of is not None:
        reversals_qs = reversals_qs.filter(entry_date__lte=as_of)

    for entry in reversals_qs.values("id", "source_type", "source_id"):
        base_type = entry["source_type"][:-9]
        owner_id = _owner_map(base_type, {entry["source_id"]}).get(entry["source_id"])
        if owner_id is None:
            continue
        totals = JournalLine.objects.filter(
            entry_id=entry["id"],
            account=account,
        ).aggregate(debit=Sum("debit"), credit=Sum("credit"))
        debit = totals["debit"] or ZERO
        credit = totals["credit"] or ZERO
        signed = debit - credit if owner_kind == "customer" else credit - debit
        result[owner_id] = result.get(owner_id, ZERO) + signed

    return result


__all__ = ("owner_ledger_balances",)
