"""Reconcile operational AR/AP subledgers against the posted general ledger."""

from decimal import Decimal

from django.db.models import Sum

from accounting.models import Account, JournalEntry, JournalLine
from accounting.services.balances import customer_balances, supplier_balances
from accounting.services.journal import get_default_company
from invoices.models import Invoice
from payments.models import PaymentRefund, PaymentTransaction
from purchases.models import Purchase, PurchaseReturn
from purchases.models import SupplierPayment

ZERO = Decimal("0.00")


def _ar_line_amount(entry_id, account_id):
    return (
        JournalLine.objects.filter(
            entry_id=entry_id,
            account_id=account_id,
            entry__status=JournalEntry.Status.POSTED,
        ).aggregate(total=Sum("debit") - Sum("credit"))["total"]
        or ZERO
    )


def _ap_line_amount(entry_id, account_id):
    return (
        JournalLine.objects.filter(
            entry_id=entry_id,
            account_id=account_id,
            entry__status=JournalEntry.Status.POSTED,
        ).aggregate(total=Sum("credit") - Sum("debit"))["total"]
        or ZERO
    )


def _source_owner_map(*, source_type, source_ids):
    """Map source IDs to customer/supplier IDs for ledger reconciliation."""
    if not source_ids:
        return {}
    if source_type.startswith("invoice.sale"):
        return dict(Invoice.objects.filter(pk__in=source_ids).values_list("pk", "customer_id"))
    if source_type == "payment.collection":
        return dict(PaymentTransaction.objects.filter(pk__in=source_ids).values_list("pk", "customer_id"))
    if source_type == "payment.refund":
        return dict(
            PaymentRefund.objects.filter(pk__in=source_ids)
            .values_list("pk", "invoice__customer_id")
        )
    if source_type.startswith("invoice.return"):
        return dict(
            Invoice.objects.filter(invoice_returns__pk__in=source_ids)
            .values_list("invoice_returns__pk", "customer_id")
        )
    if source_type.startswith("purchase.confirmation"):
        return dict(Purchase.objects.filter(pk__in=source_ids).values_list("pk", "supplier_id"))
    if source_type == "payment.supplier":
        return dict(SupplierPayment.objects.filter(pk__in=source_ids).values_list("pk", "supplier_id"))
    if source_type.startswith("purchase.return"):
        return dict(
            Purchase.objects.filter(purchase_returns__pk__in=source_ids)
            .values_list("purchase_returns__pk", "supplier_id")
        )
    return {}


def _ledger_balances(*, account_code, owner_kind):
    """Aggregate posted AR/AP entries by their business source owner."""
    company = get_default_company()
    account = Account.objects.filter(company=company, code=account_code).first()
    if account is None:
        return {}

    prefixes = (
        ("customer", ("invoice.sale", "invoice.return", "payment.collection", "payment.refund"))
        if owner_kind == "customer"
        else ("supplier", ("purchase.confirmation", "purchase.return", "payment.supplier"))
    )
    source_types = prefixes[1]
    entries = (
        JournalEntry.objects.filter(
            company=company,
            status=JournalEntry.Status.POSTED,
            source_type__in=source_types,
        )
        .values("id", "source_type", "source_id")
        .order_by("id")
    )
    ids_by_type = {}
    for entry in entries:
        ids_by_type.setdefault(entry["source_type"], set()).add(entry["source_id"])

    owner_maps = {
        source_type: _source_owner_map(source_type=source_type, source_ids=source_ids)
        for source_type, source_ids in ids_by_type.items()
    }
    result = {}
    for entry in entries:
        owner_id = owner_maps.get(entry["source_type"], {}).get(entry["source_id"])
        if owner_id is None:
            continue
        amount = (
            _ar_line_amount(entry["id"], account.pk)
            if owner_kind == "customer"
            else _ap_line_amount(entry["id"], account.pk)
        )
        result[owner_id] = result.get(owner_id, ZERO) + amount

    # Compensating entries use the original source ID with a different type.
    reversal_entries = JournalEntry.objects.filter(
        company=company,
        status=JournalEntry.Status.POSTED,
        source_type__endswith=".reversal",
    ).values("id", "source_type", "source_id")
    for entry in reversal_entries:
        base_type = entry["source_type"][:-9]
        if base_type not in source_types:
            continue
        owner_id = owner_maps.get(base_type, {}).get(entry["source_id"])
        if owner_id is None:
            owner_id = _source_owner_map(source_type=base_type, source_ids={entry["source_id"]}).get(entry["source_id"])
        if owner_id is None:
            continue
        amount = (
            _ar_line_amount(entry["id"], account.pk)
            if owner_kind == "customer"
            else _ap_line_amount(entry["id"], account.pk)
        )
        result[owner_id] = result.get(owner_id, ZERO) + amount
    return result


def reconcile_customer_balances(*, as_of=None):
    operational = {
        row["customer_id"]: row["balance"]
        for row in customer_balances(as_of=as_of)
    }
    ledger = _ledger_balances(account_code="1200", owner_kind="customer")
    owner_ids = set(operational) | set(ledger)
    return [
        {
            "customer_id": owner_id,
            "operational": operational.get(owner_id, ZERO),
            "ledger": ledger.get(owner_id, ZERO),
            "difference": operational.get(owner_id, ZERO) - ledger.get(owner_id, ZERO),
        }
        for owner_id in sorted(owner_ids)
        if operational.get(owner_id, ZERO) != ledger.get(owner_id, ZERO)
    ]


def reconcile_supplier_balances(*, as_of=None):
    operational = {
        row["supplier_id"]: row["balance"]
        for row in supplier_balances(as_of=as_of)
    }
    ledger = _ledger_balances(account_code="2100", owner_kind="supplier")
    owner_ids = set(operational) | set(ledger)
    return [
        {
            "supplier_id": owner_id,
            "operational": operational.get(owner_id, ZERO),
            "ledger": ledger.get(owner_id, ZERO),
            "difference": operational.get(owner_id, ZERO) - ledger.get(owner_id, ZERO),
        }
        for owner_id in sorted(owner_ids)
        if operational.get(owner_id, ZERO) != ledger.get(owner_id, ZERO)
    ]


def reconcile_subledgers(*, as_of=None):
    """Return all AR/AP mismatches; an empty result means the ledgers agree."""
    return {
        "customers": reconcile_customer_balances(as_of=as_of),
        "suppliers": reconcile_supplier_balances(as_of=as_of),
    }
