"""
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
         \       /
          \     /
           v   v
       Financial / AR-AP reports

analytics.py is a separate operational analytics layer.  It currently uses
Django ORM/database aggregation for request-time KPIs and is intended to gain
a Celery + Pandas/NumPy path later for heavy analytics workloads.

Boundary rule
-------------
Business-domain services may call accounting automation, while the low-level
journal engine should remain independent from domain applications.
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
)
from .balances import customer_aging, customer_balances, supplier_aging, supplier_balances
from .journal import (
    JournalEntryError,
    create_journal_entry,
    general_ledger,
    get_default_company,
    post_journal_entry,
    trial_balance,
)
from .statements import balance_sheet, cash_flow, profit_and_loss

__all__ = (
    "JournalEntryError",
    "balance_sheet",
    "cash_flow",
    "create_journal_entry",
    "customer_aging",
    "customer_balances",
    "ensure_default_accounts",
    "general_ledger",
    "get_default_company",
    "post_customer_collection",
    "post_payment_refund",
    "post_purchase",
    "post_purchase_return",
    "post_journal_entry",
    "post_sales_invoice",
    "post_sales_return",
    "post_supplier_payment",
    "profit_and_loss",
    "supplier_aging",
    "supplier_balances",
    "trial_balance",
)
