"""Read-only financial statements built from posted journal activity.

Architecture::

    POSTED JournalEntry
          |
          v
      JournalLine
          |
      +---+---+---+
      |       |   |
      v       v   v
     P&L      BS  Cash Flow

Rules:
    - Draft journal entries are excluded.
    - Revenue and expense balances drive P&L.
    - Assets, liabilities, and equity drive the balance sheet.
    - Until closing entries exist, cumulative net income is presented as
      retained earnings for balance-sheet purposes.
"""

from collections import defaultdict
from decimal import Decimal

from django.db.models import Sum

from accounting.models import Account, JournalEntry, JournalLine
from accounting.services.journal import get_default_company


ZERO = Decimal("0")


def _posted_lines(*, company, date_from=None, date_to=None):
    """Return POSTED journal lines for a company and optional date range."""
    queryset = JournalLine.objects.filter(
        entry__company=company,
        entry__status=JournalEntry.Status.POSTED,
        account__company=company,
    ).select_related("account", "entry")
    if date_from:
        queryset = queryset.filter(entry__entry_date__gte=date_from)
    if date_to:
        queryset = queryset.filter(entry__entry_date__lte=date_to)
    return queryset


def profit_and_loss(*, date_from=None, date_to=None, company=None):
    """Build P&L from posted revenue and expense accounts.

    Revenue is measured as credit minus debit; expenses are debit minus
    credit. Net income is ``total_revenue - total_expenses``.
    """
    company = company or get_default_company()
    rows = (
        _posted_lines(company=company, date_from=date_from, date_to=date_to)
        .filter(account__account_type__in=(Account.AccountType.REVENUE, Account.AccountType.EXPENSE))
        .values("account_id", "account__code", "account__name", "account__account_type")
        .annotate(total_debit=Sum("debit"), total_credit=Sum("credit"))
        .order_by("account__code")
    )

    revenue = []
    expenses = []
    total_revenue = ZERO
    total_expenses = ZERO
    for row in rows:
        debit = row["total_debit"] or ZERO
        credit = row["total_credit"] or ZERO
        if row["account__account_type"] == Account.AccountType.REVENUE:
            amount = credit - debit
            total_revenue += amount
            revenue.append({**row, "amount": amount})
        else:
            amount = debit - credit
            total_expenses += amount
            expenses.append({**row, "amount": amount})

    return {
        "revenue": revenue,
        "expenses": expenses,
        "total_revenue": total_revenue,
        "total_expenses": total_expenses,
        "net_income": total_revenue - total_expenses,
    }


def balance_sheet(*, as_of, company=None):
    """Build a balance sheet as of ``as_of``.

    The report groups asset, liability, and equity accounts. Revenue and
    expense balances are presented as cumulative retained earnings until
    closing entries are introduced.

    The result exposes ``balanced`` to verify:

        Assets == Liabilities + Equity
    """
    company = company or get_default_company()
    rows = (
        _posted_lines(company=company, date_to=as_of)
        .values("account_id", "account__code", "account__name", "account__account_type")
        .annotate(total_debit=Sum("debit"), total_credit=Sum("credit"))
        .order_by("account__code")
    )

    assets = []
    liabilities = []
    equity = []
    retained_earnings = ZERO
    total_assets = ZERO
    total_liabilities = ZERO
    total_equity = ZERO

    for row in rows:
        debit = row["total_debit"] or ZERO
        credit = row["total_credit"] or ZERO
        account_type = row["account__account_type"]

        if account_type == Account.AccountType.ASSET:
            amount = debit - credit
            total_assets += amount
            assets.append({**row, "amount": amount})
        elif account_type == Account.AccountType.LIABILITY:
            amount = credit - debit
            total_liabilities += amount
            liabilities.append({**row, "amount": amount})
        elif account_type == Account.AccountType.EQUITY:
            amount = credit - debit
            total_equity += amount
            equity.append({**row, "amount": amount})
        elif account_type in (Account.AccountType.REVENUE, Account.AccountType.EXPENSE):
            # Revenue increases retained earnings; expenses reduce it.
            retained_earnings += credit - debit

    total_equity += retained_earnings

    return {
        "as_of": as_of,
        "assets": assets,
        "liabilities": liabilities,
        "equity": equity,
        "retained_earnings": retained_earnings,
        "total_assets": total_assets,
        "total_liabilities": total_liabilities,
        "total_equity": total_equity,
        "balanced": total_assets == total_liabilities + total_equity,
    }


def cash_flow(*, date_from=None, date_to=None, company=None):
    """Build cash-flow totals from posted Cash and Bank account movements.

    The current implementation uses accounts ``1010`` (Cash) and ``1020``
    (Bank). Known payment/return source types are grouped as Operating;
    unclassified cash movements are grouped as Other.
    """
    company = company or get_default_company()
    cash_accounts = list(
        Account.objects.filter(
            company=company,
            account_type=Account.AccountType.ASSET,
            code__in=("1010", "1020"),
        ).values_list("id", "code", "name")
    )
    cash_ids = {account_id for account_id, _code, _name in cash_accounts}
    queryset = _posted_lines(company=company, date_from=date_from, date_to=date_to).filter(account_id__in=cash_ids)

    categories = defaultdict(Decimal)
    source_labels = {
        "payment.collection": "Operating",
        "payment.refund": "Operating",
        "payment.supplier": "Operating",
        "invoice.return": "Operating",
        "purchase.return": "Operating",
    }

    total_inflows = ZERO
    total_outflows = ZERO
    for line in queryset:
        amount = line.debit - line.credit
        if amount == 0:
            continue
        category = source_labels.get(line.entry.source_type, "Other")
        categories[category] += amount
        if amount > 0:
            total_inflows += amount
        else:
            total_outflows += -amount

    opening_cash = ZERO
    if date_from:
        before = _posted_lines(company=company, date_to=None).filter(
            account_id__in=cash_ids,
            entry__entry_date__lt=date_from,
        )
        opening_cash = sum(
            ((line.debit - line.credit) for line in before),
            ZERO,
        )

    ending_cash = opening_cash + sum(categories.values(), ZERO)
    return {
        "date_from": date_from,
        "date_to": date_to,
        "opening_cash": opening_cash,
        "operating": categories.get("Operating", ZERO),
        "other": categories.get("Other", ZERO),
        "net_change": sum(categories.values(), ZERO),
        "total_inflows": total_inflows,
        "total_outflows": total_outflows,
        "ending_cash": ending_cash,
    }
