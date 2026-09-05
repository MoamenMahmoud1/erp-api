from collections import defaultdict
from datetime import date
from decimal import Decimal

from django.db.models import F, Q, Sum, Value
from django.db.models.functions import Coalesce

from customers.models import Customer
from invoices.models import Invoice
from purchases.models import Purchase, PurchaseReturnItem
from suppliers.models import Supplier

ZERO = Decimal("0.00")


def _money(value):
    return value or ZERO


def customer_balances(*, as_of=None, customer_id=None):
    """Return AR balances from invoice transactions through the requested date.

    Balance = invoice total - sales returns - allocated collections + payment refunds.
    """
    invoice_filter = Q()
    if as_of:
        invoice_filter &= Q(created_at__date__lte=as_of)

    allocation_filter = Q(payment_allocations__created_at__date__lte=as_of) if as_of else Q()
    refund_filter = Q(payment_refunds__created_at__date__lte=as_of) if as_of else Q()
    return_filter = Q(returns__created_at__date__lte=as_of) if as_of else Q()

    invoices = (
        Invoice.objects.filter(invoice_filter)
        .filter(status__in=(Invoice.Status.CONFIRMED, Invoice.Status.PAID, Invoice.Status.RETURNED))
        .annotate(
            paid_amount=Coalesce(Sum("payment_allocations__cash_amount", filter=allocation_filter), Value(ZERO)),
            paid_transfer=Coalesce(Sum("payment_allocations__transfer_amount", filter=allocation_filter), Value(ZERO)),
            refunded_amount=Coalesce(Sum("payment_refunds__cash_amount", filter=refund_filter), Value(ZERO)),
            refunded_transfer=Coalesce(Sum("payment_refunds__transfer_amount", filter=refund_filter), Value(ZERO)),
            returned_amount=Coalesce(Sum("returns__refund_amount", filter=return_filter), Value(ZERO)),
        )
        .values("customer_id", "customer__name")
        .annotate(
            invoiced=Sum("coupon_discount") * Value(0),
        )
    )

    # Invoice.total is a Python property, so aggregate invoice items with the same
    # calculator rules and coupon discount rather than relying on a non-existent DB field.
    customer_rows = {}
    query = (
        Invoice.objects.filter(invoice_filter)
        .filter(status__in=(Invoice.Status.CONFIRMED, Invoice.Status.PAID, Invoice.Status.RETURNED))
        .select_related("customer")
        .prefetch_related("items")
        .order_by("customer_id", "id")
    )
    for invoice in query:
        total = invoice.total
        paid = sum((a.total_amount for a in invoice.payment_allocations.all() if not as_of or a.created_at.date() <= as_of), ZERO)
        refunded = sum((r.total_amount for r in invoice.payment_refunds.all() if not as_of or r.created_at.date() <= as_of), ZERO)
        returned = sum((r.refund_amount for r in invoice.returns.all() if not as_of or r.created_at.date() <= as_of), ZERO)
        balance = total - returned - paid + refunded
        row = customer_rows.setdefault(
            invoice.customer_id,
            {"customer_id": invoice.customer_id, "customer_name": invoice.customer.name, "invoiced": ZERO, "paid": ZERO, "refunded": ZERO, "returns": ZERO, "balance": ZERO},
        )
        row["invoiced"] += total
        row["paid"] += paid
        row["refunded"] += refunded
        row["returns"] += returned
        row["balance"] += balance

    if customer_id is not None:
        return [row for row in customer_rows.values() if row["customer_id"] == customer_id]
    return list(customer_rows.values())


def supplier_balances(*, as_of=None, supplier_id=None):
    """Return AP balances from confirmed purchases through the requested date.

    Balance = purchase total - purchase returns - supplier payment allocations.
    """
    purchase_filter = Q(status=Purchase.Status.CONFIRMED)
    if as_of:
        purchase_filter &= Q(created_at__date__lte=as_of)

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
            (item.unit_price * item.quantity for ret in purchase.returns.all() if not as_of or ret.created_at.date() <= as_of for item in ret.items.all()),
            ZERO,
        )
        allocated = sum(
            (allocation.total_amount for allocation in purchase.supplier_payment_allocations.all() if not as_of or allocation.created_at.date() <= as_of),
            ZERO,
        )
        balance = total - returned - allocated
        row = supplier_rows.setdefault(
            purchase.supplier_id,
            {"supplier_id": purchase.supplier_id, "supplier_name": purchase.supplier.name, "purchased": ZERO, "paid": ZERO, "returns": ZERO, "balance": ZERO},
        )
        row["purchased"] += total
        row["paid"] += allocated
        row["returns"] += returned
        row["balance"] += balance

    if supplier_id is not None:
        return [row for row in supplier_rows.values() if row["supplier_id"] == supplier_id]
    return list(supplier_rows.values())


def _age_bucket(days):
    if days <= 30:
        return "0_30"
    if days <= 60:
        return "31_60"
    if days <= 90:
        return "61_90"
    return "90_plus"


def _empty_aging():
    return {"0_30": ZERO, "31_60": ZERO, "61_90": ZERO, "90_plus": ZERO}


def customer_aging(*, as_of=None, customer_id=None):
    as_of = as_of or date.today()
    balances = customer_balances(as_of=as_of, customer_id=customer_id)
    open_rows = []

    invoice_filter = Q(created_at__date__lte=as_of)
    if customer_id is not None:
        invoice_filter &= Q(customer_id=customer_id)
    invoices = (
        Invoice.objects.filter(invoice_filter)
        .filter(status__in=(Invoice.Status.CONFIRMED, Invoice.Status.PAID, Invoice.Status.RETURNED))
        .select_related("customer")
        .prefetch_related("items", "payment_allocations", "payment_refunds", "returns")
        .order_by("customer_id", "created_at", "id")
    )
    by_customer = defaultdict(_empty_aging)
    for invoice in invoices:
        total = invoice.total
        paid = sum((a.total_amount for a in invoice.payment_allocations.all() if a.created_at.date() <= as_of), ZERO)
        refunded = sum((r.total_amount for r in invoice.payment_refunds.all() if r.created_at.date() <= as_of), ZERO)
        returned = sum((r.refund_amount for r in invoice.returns.all() if r.created_at.date() <= as_of), ZERO)
        outstanding = total - paid - returned + refunded
        if outstanding <= ZERO:
            continue
        bucket = _age_bucket((as_of - invoice.created_at.date()).days)
        by_customer[invoice.customer_id][bucket] += outstanding

    names = {row["customer_id"]: row["customer_name"] for row in balances}
    for cid, buckets in by_customer.items():
        open_rows.append({"customer_id": cid, "customer_name": names.get(cid, Customer.objects.get(pk=cid).name), **buckets, "total": sum(buckets.values(), ZERO)})
    return open_rows


def supplier_aging(*, as_of=None, supplier_id=None):
    as_of = as_of or date.today()
    by_supplier = defaultdict(_empty_aging)
    purchase_filter = Q(status=Purchase.Status.CONFIRMED, created_at__date__lte=as_of)
    if supplier_id is not None:
        purchase_filter &= Q(supplier_id=supplier_id)
    purchases = (
        Purchase.objects.filter(purchase_filter)
        .select_related("supplier")
        .prefetch_related("items", "returns__items", "supplier_payment_allocations")
        .order_by("supplier_id", "created_at", "id")
    )
    names = {}
    for purchase in purchases:
        names[purchase.supplier_id] = purchase.supplier.name
        returned = sum(
            (item.unit_price * item.quantity for ret in purchase.returns.all() if ret.created_at.date() <= as_of for item in ret.items.all()),
            ZERO,
        )
        paid = sum((a.total_amount for a in purchase.supplier_payment_allocations.all() if a.created_at.date() <= as_of), ZERO)
        outstanding = purchase.total_amount - returned - paid
        if outstanding <= ZERO:
            continue
        bucket = _age_bucket((as_of - purchase.created_at.date()).days)
        by_supplier[purchase.supplier_id][bucket] += outstanding

    return [
        {"supplier_id": sid, "supplier_name": names[sid], **buckets, "total": sum(buckets.values(), ZERO)}
        for sid, buckets in by_supplier.items()
    ]
