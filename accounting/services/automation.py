from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from accounting.models import Account, JournalEntry
from accounting.services.journal import (
    JournalEntryError,
    create_journal_entry,
    get_default_company,
    post_journal_entry,
)


DEFAULT_ACCOUNTS = {
    "inventory": ("1100", "Inventory", Account.AccountType.ASSET),
    "accounts_receivable": ("1200", "Accounts Receivable", Account.AccountType.ASSET),
    "cash": ("1010", "Cash", Account.AccountType.ASSET),
    "bank": ("1020", "Bank", Account.AccountType.ASSET),
    "accounts_payable": ("2100", "Accounts Payable", Account.AccountType.LIABILITY),
    "sales_revenue": ("4100", "Sales Revenue", Account.AccountType.REVENUE),
    "sales_returns": ("4200", "Sales Returns", Account.AccountType.REVENUE),
    "cost_of_goods_sold": ("5100", "Cost of Goods Sold", Account.AccountType.EXPENSE),
}


def ensure_default_accounts(company=None):
    company = company or get_default_company()
    with transaction.atomic():
        for code, name, account_type in DEFAULT_ACCOUNTS.values():
            Account.objects.get_or_create(
                company=company,
                code=code,
                defaults={"name": name, "account_type": account_type},
            )
    return {
        key: Account.objects.get(company=company, code=code)
        for key, (code, _name, _type) in DEFAULT_ACCOUNTS.items()
    }


def _source_entry(company, source_type, source_id):
    return (
        JournalEntry.objects.filter(
            company=company,
            source_type=source_type,
            source_id=source_id,
            status=JournalEntry.Status.POSTED,
        )
        .first()
    )


def _source_lines(entry):
    return list(entry.lines.all())


def post_sales_invoice(*, invoice, actor_id, company=None):
    company = company or get_default_company()
    existing = _source_entry(company, "invoice.sale", invoice.pk)
    if existing:
        return existing

    accounts = ensure_default_accounts(company)
    receivable = invoice.total
    cogs = sum(
        (item.product.purchase_price * item.quantity for item in invoice.items.all()),
        Decimal("0"),
    )
    lines = [
        {"account_id": accounts["accounts_receivable"].pk, "debit": receivable, "credit": 0},
        {"account_id": accounts["sales_revenue"].pk, "debit": 0, "credit": receivable},
    ]
    if cogs > 0:
        lines.extend(
            [
                {"account_id": accounts["cost_of_goods_sold"].pk, "debit": cogs, "credit": 0},
                {"account_id": accounts["inventory"].pk, "debit": 0, "credit": cogs},
            ]
        )

    entry = create_journal_entry(
        created_by_id=actor_id,
        entry_date=timezone.localdate(invoice.created_at),
        description=f"Sale for invoice #{invoice.pk}",
        reference=f"Invoice #{invoice.pk}",
        source_type="invoice.sale",
        source_id=invoice.pk,
        lines=lines,
        company=company,
    )
    return post_journal_entry(entry_id=entry.pk, actor_id=actor_id, company=company)


def post_purchase(*, purchase, actor_id, company=None):
    company = company or get_default_company()
    existing = _source_entry(company, "purchase.confirmation", purchase.pk)
    if existing:
        return existing

    accounts = ensure_default_accounts(company)
    total = purchase.total_amount
    lines = [
        {"account_id": accounts["inventory"].pk, "debit": total, "credit": 0},
        {"account_id": accounts["accounts_payable"].pk, "debit": 0, "credit": total},
    ]
    entry = create_journal_entry(
        created_by_id=actor_id,
        entry_date=timezone.localdate(purchase.created_at),
        description=f"Purchase #{purchase.pk}",
        reference=purchase.reference or f"Purchase #{purchase.pk}",
        source_type="purchase.confirmation",
        source_id=purchase.pk,
        lines=lines,
        company=company,
    )
    return post_journal_entry(entry_id=entry.pk, actor_id=actor_id, company=company)


def post_customer_collection(*, payment, actor_id, company=None):
    company = company or get_default_company()
    source_type = "payment.collection"
    existing = _source_entry(company, source_type, payment.pk)
    if existing:
        return existing

    accounts = ensure_default_accounts(company)
    cash = payment.cash_amount
    transfer = payment.transfer_amount
    total = payment.total_amount
    lines = []
    if cash > 0:
        lines.append({"account_id": accounts["cash"].pk, "debit": cash, "credit": 0})
    if transfer > 0:
        lines.append({"account_id": accounts["bank"].pk, "debit": transfer, "credit": 0})
    lines.append({"account_id": accounts["accounts_receivable"].pk, "debit": 0, "credit": total})

    entry = create_journal_entry(
        created_by_id=actor_id,
        entry_date=timezone.localdate(payment.created_at),
        description=f"Customer collection #{payment.pk}",
        reference=f"Payment #{payment.pk}",
        source_type=source_type,
        source_id=payment.pk,
        lines=lines,
        company=company,
    )
    return post_journal_entry(entry_id=entry.pk, actor_id=actor_id, company=company)
