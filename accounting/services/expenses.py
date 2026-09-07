"""Business service for recording paid operating expenses.

    Expense
       |
       v
    expenses.py
       |
       v
    journal.py
       |
       +--> Dr Expense account
       +--> Cr Cash / Bank account

The service intentionally handles only paid expenses. Unpaid liabilities should
use Accounts Payable and the existing supplier-payment flow.
"""

from decimal import Decimal

from django.db import transaction

from accounting.models import Account, Expense
from accounting.services.journal import (
    create_journal_entry,
    get_default_company,
    post_journal_entry,
)
from common.exceptions import InvalidBusinessOperation


@transaction.atomic
def create_expense(
    *,
    amount,
    expense_account,
    payment_account,
    expense_date,
    description,
    reference="",
    created_by_id,
    company=None,
):
    """Create and immediately post a paid expense.

    ``expense_account`` must be an EXPENSE account. ``payment_account`` must be
    an ASSET account, normally Cash or Bank.
    """
    company = company or get_default_company()
    expense_account = Account.objects.get(pk=expense_account, company=company)
    payment_account = Account.objects.get(pk=payment_account, company=company)

    if amount <= Decimal("0"):
        raise InvalidBusinessOperation("Expense amount must be greater than zero.")
    if expense_account.account_type != Account.AccountType.EXPENSE:
        raise InvalidBusinessOperation(
            "The expense account must be an expense account."
        )
    if payment_account.account_type != Account.AccountType.ASSET:
        raise InvalidBusinessOperation(
            "The payment account must be an asset account."
        )
    if not description.strip():
        raise InvalidBusinessOperation("Expense description is required.")

    from accounting.services.periods import assert_period_open

    assert_period_open(entry_date=expense_date, company=company)

    expense = Expense.objects.create(
        company=company,
        expense_account=expense_account,
        payment_account=payment_account,
        amount=amount,
        expense_date=expense_date,
        description=description,
        reference=reference,
        created_by_id=created_by_id,
    )
    entry = create_journal_entry(
        created_by_id=created_by_id,
        entry_date=expense_date,
        description=description,
        reference=reference or f"Expense #{expense.pk}",
        source_type="expense",
        source_id=expense.pk,
        lines=[
            {"account_id": expense_account.pk, "debit": amount, "credit": 0},
            {"account_id": payment_account.pk, "debit": 0, "credit": amount},
        ],
        company=company,
    )
    post_journal_entry(entry_id=entry.pk, actor_id=created_by_id, company=company)
    return expense
