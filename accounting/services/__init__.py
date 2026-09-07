r"""
Accounting Services Package
===========================

Service boundaries
------------------

    Business operations
            |
            v
      automation.py
            |
            v
        journal.py
            |
            v
       Posted Ledger
          /     \
         v       v
 statements.py  balances.py

Small accounting workflows are kept in dedicated services only when they have
an independent business rule:

    expenses.py  -> paid operating expenses
    opening.py   -> initial opening balance
    periods.py   -> date-range posting lock

analytics.py is a separate operational analytics layer.
"""

from .automation import (
    ensure_default_accounts,
    post_customer_collection,
    post_payment_refund,
    post_purchase,
    post_purchase_return,
    post_sales_invoice,
    post_sales_return,
    post_supplier_payment,
    reverse_source_entry,
)
from .balances import customer_aging, customer_balances, supplier_aging, supplier_balances
from .expenses import create_expense
from .journal import (
    JournalEntryError,
    create_journal_entry,
    general_ledger,
    get_default_company,
    post_journal_entry,
    trial_balance,
)
from .opening import create_opening_balance
from .periods import AccountingPeriodError, assert_period_open, close_period, create_period
from .statements import balance_sheet, cash_flow, profit_and_loss

__all__ = (
    "AccountingPeriodError",
    "JournalEntryError",
    "assert_period_open",
    "balance_sheet",
    "cash_flow",
    "close_period",
    "create_expense",
    "create_journal_entry",
    "create_opening_balance",
    "create_period",
    "customer_aging",
    "customer_balances",
    "ensure_default_accounts",
    "general_ledger",
    "get_default_company",
    "post_customer_collection",
    "post_journal_entry",
    "post_payment_refund",
    "post_purchase",
    "post_purchase_return",
    "post_sales_invoice",
    "post_sales_return",
    "post_supplier_payment",
    "profit_and_loss",
    "reverse_source_entry",
    "supplier_aging",
    "supplier_balances",
    "trial_balance",
)
