from collections import defaultdict
from decimal import Decimal

from django.db.models import Sum

from accounting.models import Account, JournalEntry, JournalLine
from accounting.services.journal import get_default_company


ZERO = Decimal("0")


def _posted_lines(*, company, date_from=None, date_to=None):
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
        if account_type in (Account.AccountType.ASSET, Account.AccountType.LIABILITY, Account.AccountType.EQUITY):
            if account_type == Account.AccountType.ASSET:
                amount = debit - credit
                total_assets += amount
                assets.append({**row, "amount": amount})
            elif account_type == Account.AccountType.LIABILITY:
                amount = credit - debit
                total_liabilities += amount
                liabilities.append({**row, "amount": amount})
            else:
                amount = credit - debit
                total_equity += amount
                equity.append({**row, "amount": amount})
        elif account_type in (Account.AccountType.REVENUE, Account.AccountType.EXPENSE):
            retained_earnings += credit - debit if account_type == Account.AccountType.REVENUE else debit - credit

    # Revenue and expense accounts are temporary accounts; until closing entries exist,
    # their cumulative net income belongs in equity for balance-sheet presentation.
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
