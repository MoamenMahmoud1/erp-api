"""
Accounting Journal Service
==========================

Purpose
-------
The journal service is the low-level accounting engine.  It knows how to
validate, create, post, and read journal entries; it does not know about
invoices, purchases, or payments.

Architecture
------------

    Business operation
            |
            v
      automation.py
            |
            v
      journal.py
            |
            +-------------------+
            |                   |
            v                   v
      JournalEntry         JournalLine
            |                   |
            +---------+---------+
                      |
                      v
                    Account

Write path:
    validate -> create (DRAFT) -> post (POSTED)

Read path:
    POSTED JournalLines -> General Ledger / Trial Balance

Accounting invariant:
    Total Debit == Total Credit

Important
---------
Only POSTED entries are considered by ledger and financial-reporting reads.
"""

from decimal import Decimal

from django.db import transaction
from django.db.models import Max, Sum
from django.utils import timezone

from accounting.models import Account, JournalEntry, JournalLine
from common.exceptions import InvalidBusinessOperation, InvalidStateTransition
from organization.models import Company


class JournalEntryError(InvalidBusinessOperation):
    """Raised when an accounting journal violates a business rule."""


def get_default_company():
    """
    Return the company's singleton accounting context.

    Why it exists:
        Accounting entries must belong to a company.  The current ERP uses
        the company's singleton marker as the default accounting context.

    Returns:
        Company: the active/default company.

    Raises:
        JournalEntryError: if no default company exists.
    """
    try:
        return Company.objects.get(singleton_marker=True)
    except Company.DoesNotExist as exc:
        raise JournalEntryError("A company must exist before accounting can be used.") from exc


def _validate_lines(lines, company):
    """
    Validate the accounting lines before a journal is persisted or posted.

    Rules enforced:
        1. A journal must contain at least two lines.
        2. Every referenced account must belong to the same company.
        3. Each line must contain a debit OR a credit, never both or neither.
        4. Debit and credit amounts cannot be negative.
        5. Total debits must equal total credits.
        6. The journal total must be greater than zero.

    Conceptual flow:

        Journal Lines
             |
             v
        Validate structure
             |
             v
        Validate company ownership
             |
             v
        Validate Debit / Credit
             |
             v
        Validate balance

    Returns:
        tuple[Decimal, Decimal]: total debit and total credit.

    Raises:
        JournalEntryError: when any accounting rule is violated.
    """
    if not lines:
        raise JournalEntryError("A journal entry must contain at least two lines.")

    total_debit = Decimal("0")
    total_credit = Decimal("0")
    account_ids = {line["account_id"] for line in lines}
    accounts = {line_account.pk: line_account for line_account in Account.objects.filter(pk__in=account_ids, company=company)}
    if len(accounts) != len(account_ids):
        raise JournalEntryError("Every journal line account must belong to the company.")

    for line in lines:
        debit = Decimal(line.get("debit", 0))
        credit = Decimal(line.get("credit", 0))
        if (debit > 0) == (credit > 0):
            raise JournalEntryError("Each journal line must have either a debit or a credit amount.")
        if debit < 0 or credit < 0:
            raise JournalEntryError("Debit and credit amounts cannot be negative.")
        total_debit += debit
        total_credit += credit

    if total_debit != total_credit:
        raise JournalEntryError("Journal entry is not balanced: total debits must equal total credits.")
    if total_debit <= 0:
        raise JournalEntryError("Journal entry total must be greater than zero.")
    return total_debit, total_credit


@transaction.atomic
def create_journal_entry(
    *,
    created_by_id,
    entry_date,
    description="",
    reference="",
    source_type="",
    source_id=None,
    lines,
    company=None,
):
    """
    Create a new journal entry in DRAFT state.

    What this function does:
        1. Resolve the company context.
        2. Lock the company row while allocating the next journal number.
        3. Validate all journal lines.
        4. Generate the next journal number for that company.
        5. Create the JournalEntry header.
        6. Create all JournalLine records in bulk.

    Important:
        This function creates the journal but does not post it.  Posting is
        a separate state transition handled by post_journal_entry().

    Transaction boundary:
        The entry header and all of its lines are created atomically.  If any
        step fails, the whole operation is rolled back.

    Returns:
        JournalEntry: the newly created DRAFT entry.

    Raises:
        JournalEntryError: when validation fails.
    """
    company = company or get_default_company()
    company = Company.objects.select_for_update().get(pk=company.pk)
    _validate_lines(lines, company)
    next_number = (
        JournalEntry.objects.filter(company=company).aggregate(max_number=Max("number"))["max_number"] or 0
    ) + 1
    entry = JournalEntry.objects.create(
        company=company,
        number=next_number,
        entry_date=entry_date,
        description=description,
        reference=reference,
        source_type=source_type,
        source_id=source_id,
        created_by_id=created_by_id,
        status=JournalEntry.Status.DRAFT,
    )
    JournalLine.objects.bulk_create(
        [
            JournalLine(
                entry=entry,
                account_id=line["account_id"],
                description=line.get("description", ""),
                debit=line.get("debit", 0),
                credit=line.get("credit", 0),
            )
            for line in lines
        ]
    )
    return entry


@transaction.atomic
def post_journal_entry(*, entry_id, actor_id, company=None):
    """
    Transition a valid journal entry from DRAFT to POSTED.

    Why it is separate from creation:
        A draft can be prepared and reviewed before becoming part of the
        official accounting ledger.

    Concurrency protection:
        The entry row is locked with select_for_update() so two concurrent
        requests cannot post the same journal successfully.

    Returns:
        JournalEntry: the POSTED entry.

    Raises:
        JournalEntryError: if the entry belongs to another company.
        InvalidStateTransition: if the entry is not a DRAFT.
    """
    entry = (
        JournalEntry.objects.select_for_update()
        .select_related("company")
        .prefetch_related("lines__account")
        .get(pk=entry_id)
    )
    if company is not None and entry.company_id != company.pk:
        raise JournalEntryError("Journal entry does not belong to the active company.")
    if entry.status != JournalEntry.Status.DRAFT:
        raise InvalidStateTransition("Only a draft journal entry can be posted.")

    lines = list(entry.lines.all())
    _validate_lines(
        [
            {"account_id": line.account_id, "debit": line.debit, "credit": line.credit}
            for line in lines
        ],
        entry.company,
    )
    entry.status = JournalEntry.Status.POSTED
    entry.posted_by_id = actor_id
    entry.posted_at = timezone.now()
    entry.save(update_fields=("status", "posted_by", "posted_at", "updated_at"))
    return entry


def general_ledger(*, account_id, date_from=None, date_to=None, company=None):
    """
    Return the posted activity and running balance for one account.

    Input:
        account_id: account to inspect.
        date_from/date_to: optional inclusive posting-date filters.

    Balance rule:
        Debit-normal accounts increase with debit and decrease with credit.
        Credit-normal accounts increase with credit and decrease with debit.

    Returns:
        tuple[Account, list[dict]]: the account plus ordered ledger rows.
    """
    company = company or get_default_company()
    account = Account.objects.get(pk=account_id, company=company)
    queryset = JournalLine.objects.filter(
        account=account,
        entry__company=company,
        entry__status=JournalEntry.Status.POSTED,
    ).select_related("entry").order_by("entry__entry_date", "entry__number", "pk")
    if date_from:
        queryset = queryset.filter(entry__entry_date__gte=date_from)
    if date_to:
        queryset = queryset.filter(entry__entry_date__lte=date_to)

    running = Decimal("0")
    result = []
    for line in queryset:
        if account.normal_side == "debit":
            running += line.debit - line.credit
        else:
            running += line.credit - line.debit
        result.append({
            "entry_number": line.entry.number,
            "entry_date": line.entry.entry_date,
            "description": line.description or line.entry.description,
            "reference": line.entry.reference,
            "debit": line.debit,
            "credit": line.credit,
            "balance": running,
        })
    return account, result


def trial_balance(*, date_from=None, date_to=None, company=None):
    """
    Summarize all posted account activity for a period.

    The trial balance groups posted journal lines by account and returns the
    total debits and credits for each account plus grand totals.

    Main invariant:
        total_debit == total_credit for a healthy double-entry ledger.

    Returns:
        tuple[list[dict], Decimal, Decimal]: account rows, total debit, total
        credit.
    """
    company = company or get_default_company()
    queryset = JournalLine.objects.filter(
        entry__company=company,
        entry__status=JournalEntry.Status.POSTED,
        account__company=company,
    )
    if date_from:
        queryset = queryset.filter(entry__entry_date__gte=date_from)
    if date_to:
        queryset = queryset.filter(entry__entry_date__lte=date_to)

    rows = (
        queryset.values("account_id", "account__code", "account__name", "account__account_type")
        .annotate(total_debit=Sum("debit"), total_credit=Sum("credit"))
        .order_by("account__code")
    )
    result = []
    total_debit = Decimal("0")
    total_credit = Decimal("0")
    for row in rows:
        debit = row["total_debit"] or Decimal("0")
        credit = row["total_credit"] or Decimal("0")
        total_debit += debit
        total_credit += credit
        result.append({**row, "debit": debit, "credit": credit, "balance": debit - credit})
    return result, total_debit, total_credit
