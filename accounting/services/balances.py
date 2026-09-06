"""
Accounts Receivable / Accounts Payable Service
================================================

Purpose
-------
Provide operational customer and supplier balances plus aging analysis.

Unlike `statements.py`, this module currently works from business-domain
records (invoices, purchases, payments, returns) rather than deriving the
answer directly from the general ledger.

Architecture
------------

    Customer side

    Invoice ----+
               |
    Collection-+----> Customer Balance ----> AR Aging
               |
    Refund ----+
               |
    Return ----+

    Supplier side

    Purchase --------+
                    |
    Supplier Payment-+--> Supplier Balance -> AP Aging
                    |
    Purchase Return-+

Balance formulas
----------------

    Customer balance
        Invoice total
        - Returns
        - Allocated collections
        + Payment refunds

    Supplier balance
        Purchase total
        - Purchase returns
        - Supplier payment allocations

Aging buckets
-------------
    0-30 days | 31-60 days | 61-90 days | 90+ days
"""

from collections import defaultdict
from datetime import date
from decimal import Decimal

from django.db.models import Q

from invoices.models import Invoice
from purchases.models import Purchase

ZERO = Decimal("0.00")


def customer_balances(*, as_of=None, customer_id=None):
    """
    Calculate outstanding receivables for customers as of a date.

    The calculation follows the operational invoice lifecycle:

        Invoices - Returns - Payments + Refunds = Balance

    Args:
        as_of: optional inclusive date.  Only activity on or before this date
            is included.
        customer_id: optional customer filter.

    Returns:
        list[dict]: one summary row per customer.
    """
    invoice_filter = Q()
    if as_of:
        invoice_filter &= Q(created_at__date__lte=as_of)
    if customer_id is not None:
        invoice_filter &= Q(customer_id=customer_id)

    invoices = (
        Invoice.objects.filter(invoice_filter)
        .filter(status__in=(Invoice.Status.CONFIRMED, Invoice.Status.PAID, Invoice.Status.RETURNED))
        .select_related("customer")
        .prefetch_related("items", "payment_allocations", "payment_refunds", "returns")
        .order_by("customer_id", "id")
    )
    customer_rows = {}
    for invoice in invoices:
        total = invoice.total
        paid = sum((a.total_amount for a in invoice.payment_allocations.all() if not as_of or a.created_at.date() <= as_of), ZERO)
        refunded = sum((r.total_amount for r in invoice.payment_refunds.all() if not as_of or r.created_at.date() <= as_of), ZERO)
        returned = sum((r.refund_amount for r in invoice.returns.all() if not as_of or r.created_at.date() <= as_of), ZERO)
        row = customer_rows.setdefault(
            invoice.customer_id,
            {
                "customer_id": invoice.customer_id,
                "customer_name": invoice.customer.name,
                "invoiced": ZERO,
                "paid": ZERO,
                "refunded": ZERO,
                "returns": ZERO,
                "balance": ZERO,
            },
        )
        row["invoiced"] += total
        row["paid"] += paid
        row["refunded"] += refunded
        row["returns"] += returned
        row["balance"] += total - returned - paid + refunded
    return list(customer_rows.values())


def supplier_balances(*, as_of=None, supplier_id=None):
    """
    Calculate outstanding payables for suppliers as of a date.

    The calculation follows the operational purchase lifecycle:

        Purchases - Returns - Supplier Payments = Balance

    Args:
        as_of: optional inclusive date.  Only activity on or before this date
            is included.
        supplier_id: optional supplier filter.

    Returns:
        list[dict]: one summary row per supplier.
    """
    purchase_filter = Q(status=Purchase.Status.CONFIRMED)
    if as_of:
        purchase_filter &= Q(created_at__date__lte=as_of)
    if supplier_id is not None:
        purchase_filter &= Q(supplier_id=supplier_id)

    purchases = (
        Purchase.objects.filter(purchase_filter)
        .select_related("supplier")
        .prefetch_related("items", "returns__items", "supplier_payment_allocations")
        .order_by("supplier_id", "id")
    )
    supplier_rows = {}
    for purchase in purchases:
        total = purchase.total_amount
        returned = sum(
            (
                item.unit_price * item.quantity
                for ret in purchase.returns.all()
                if not as_of or ret.created_at.date() <= as_of
                for item in ret.items.all()
            ),
            ZERO,
        )
        paid = sum(
            (
                allocation.total_amount
                for allocation in purchase.supplier_payment_allocations.all()
                if not as_of or allocation.created_at.date() <= as_of
            ),
            ZERO,
        )
        row = supplier_rows.setdefault(
            purchase.supplier_id,
            {
                "supplier_id": purchase.supplier_id,
                "supplier_name": purchase.supplier.name,
                "purchased": ZERO,
                "paid": ZERO,
                "returns": ZERO,
                "balance": ZERO,
            },
        )
        row["purchased"] += total
        row["paid"] += paid
        row["returns"] += returned
        row["balance"] += total - returned - paid
    return list(supplier_rows.values())


def _age_bucket(days):
    """
    Map an overdue age in days to the standard aging bucket.

    Buckets:
        0_30, 31_60, 61_90, 90_plus

    Returns:
        str: the bucket key.
    """
    if days <= 30:
        return "0_30"
    if days <= 60:
        return "31_60"
    if days <= 90:
        return "61_90"
    return "90_plus"


def _empty_aging():
    """Return an initialized aging-bucket mapping with zero balances."""
    return {"0_30": ZERO, "31_60": ZERO, "61_90": ZERO, "90_plus": ZERO}


def customer_aging(*, as_of=None, customer_id=None):
    """
    Distribute each customer's outstanding receivable into aging buckets.

    The age is measured from the invoice creation date to ``as_of``.  Fully
    settled invoices are skipped; only outstanding balances contribute to a
    bucket.

    Returns:
        list[dict]: customer totals split into 0-30, 31-60, 61-90, and 90+ days.
    """
    as_of = as_of or date.today()
    invoice_filter = Q(
        created_at__date__lte=as_of,
        status__in=(Invoice.Status.CONFIRMED, Invoice.Status.PAID, Invoice.Status.RETURNED),
    )
    if customer_id is not None:
        invoice_filter &= Q(customer_id=customer_id)

    invoices = (
        Invoice.objects.filter(invoice_filter)
        .select_related("customer")
        .prefetch_related("items", "payment_allocations", "payment_refunds", "returns")
        .order_by("customer_id", "created_at", "id")
    )
    by_customer = defaultdict(_empty_aging)
    names = {}
    for invoice in invoices:
        names[invoice.customer_id] = invoice.customer.name
        total = invoice.total
        paid = sum((a.total_amount for a in invoice.payment_allocations.all() if a.created_at.date() <= as_of), ZERO)
        refunded = sum((r.total_amount for r in invoice.payment_refunds.all() if r.created_at.date() <= as_of), ZERO)
        returned = sum((r.refund_amount for r in invoice.returns.all() if r.created_at.date() <= as_of), ZERO)
        outstanding = total - paid - returned + refunded
        if outstanding <= ZERO:
            continue
        by_customer[invoice.customer_id][_age_bucket((as_of - invoice.created_at.date()).days)] += outstanding

    return [
        {
            "customer_id": cid,
            "customer_name": names[cid],
            **buckets,
            "total": sum(buckets.values(), ZERO),
        }
        for cid, buckets in sorted(by_customer.items())
    ]


def supplier_aging(*, as_of=None, supplier_id=None):
    """
    Distribute each supplier's outstanding payable into aging buckets.

    The age is measured from the purchase creation date to ``as_of``.  Fully
    settled purchases are skipped; only outstanding balances contribute to a
    bucket.

    Returns:
        list[dict]: supplier totals split into 0-30, 31-60, 61-90, and 90+ days.
    """
    as_of = as_of or date.today()
    purchase_filter = Q(status=Purchase.Status.CONFIRMED, created_at__date__lte=as_of)
    if supplier_id is not None:
        purchase_filter &= Q(supplier_id=supplier_id)

    purchases = (
        Purchase.objects.filter(purchase_filter)
        .select_related("supplier")
        .prefetch_related("items", "returns__items", "supplier_payment_allocations")
        .order_by("supplier_id", "created_at", "id")
    )
    by_supplier = defaultdict(_empty_aging)
    names = {}
    for purchase in purchases:
        names[purchase.supplier_id] = purchase.supplier.name
        returned = sum(
            (
                item.unit_price * item.quantity
                for ret in purchase.returns.all()
                if ret.created_at.date() <= as_of
                for item in ret.items.all()
            ),
            ZERO,
        )
        paid = sum(
            (allocation.total_amount for allocation in purchase.supplier_payment_allocations.all() if allocation.created_at.date() <= as_of),
            ZERO,
        )
        outstanding = purchase.total_amount - returned - paid
        if outstanding <= ZERO:
            continue
        by_supplier[purchase.supplier_id][_age_bucket((as_of - purchase.created_at.date()).days)] += outstanding

    return [
        {
            "supplier_id": sid,
            "supplier_name": names[sid],
            **buckets,
            "total": sum(buckets.values(), ZERO),
        }
        for sid, buckets in sorted(by_supplier.items())
    ]
