"""Reconcile operational AR/AP details against canonical posted GL balances."""

from accounting.services.balances import customer_balances, supplier_balances


def reconcile_customer_balances(*, as_of=None):
    rows = customer_balances(as_of=as_of)
    return [
        {
            "customer_id": row["customer_id"],
            "operational": row["operational_balance"],
            "ledger": row["ledger_balance"],
            "difference": row["operational_balance"] - row["ledger_balance"],
        }
        for row in rows
        if row["operational_balance"] != row["ledger_balance"]
    ]


def reconcile_supplier_balances(*, as_of=None):
    rows = supplier_balances(as_of=as_of)
    return [
        {
            "supplier_id": row["supplier_id"],
            "operational": row["operational_balance"],
            "ledger": row["ledger_balance"],
            "difference": row["operational_balance"] - row["ledger_balance"],
        }
        for row in rows
        if row["operational_balance"] != row["ledger_balance"]
    ]


def reconcile_subledgers(*, as_of=None):
    return {
        "customers": reconcile_customer_balances(as_of=as_of),
        "suppliers": reconcile_supplier_balances(as_of=as_of),
    }


__all__ = ("reconcile_subledgers", "reconcile_customer_balances", "reconcile_supplier_balances")
