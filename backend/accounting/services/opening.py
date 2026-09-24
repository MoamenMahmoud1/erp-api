"""Service for importing a company's initial accounting balances.

An opening balance is stored as one normal, POSTED journal entry with a fixed
source key per company. Later corrections can use normal journal adjustments.
"""

from django.db import transaction

from accounting.models import Account, JournalEntry
from accounting.services.journal import (
    create_journal_entry,
    get_default_company,
    post_journal_entry,
)
from common.exceptions import InvalidBusinessOperation


@transaction.atomic
def create_opening_balance(*, entry_date, lines, created_by_id, company=None):
    """Create the company's single initial opening-balance journal.

    Opening balances may only use Asset, Liability, or Equity accounts because
    Revenue and Expense accounts start the new accounting period at zero.
    """
    company = company or get_default_company()
    if JournalEntry.objects.filter(
        company=company,
        source_type="opening_balance",
        source_id=company.pk,
    ).exists():
        raise InvalidBusinessOperation(
            "An opening balance already exists for this company."
        )

    if JournalEntry.objects.filter(
        company=company,
        status=JournalEntry.Status.POSTED,
        entry_date__lt=entry_date,
    ).exists():
        raise InvalidBusinessOperation(
            "Opening balance date must not be later than existing posted accounting entries."
        )

    account_ids = {line["account_id"] for line in lines}
    accounts = Account.objects.filter(company=company, pk__in=account_ids)
    allowed_types = {
        Account.AccountType.ASSET,
        Account.AccountType.LIABILITY,
        Account.AccountType.EQUITY,
    }
    if accounts.exclude(account_type__in=allowed_types).exists():
        raise InvalidBusinessOperation(
            "Opening balances may only use asset, liability, or equity accounts."
        )

    if accounts.count() != len(account_ids):
        raise InvalidBusinessOperation(
            "Every opening balance account must belong to the company."
        )

    entry = create_journal_entry(
        created_by_id=created_by_id,
        entry_date=entry_date,
        description="Opening balance",
        reference="Opening balance",
        source_type="opening_balance",
        source_id=company.pk,
        lines=lines,
        company=company,
    )
    return post_journal_entry(
        entry_id=entry.pk,
        actor_id=created_by_id,
        company=company,
    )
