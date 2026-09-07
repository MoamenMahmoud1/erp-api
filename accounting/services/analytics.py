"""Fast operational analytics for ERP dashboards.

Architecture::

    ERP business data
          |
          v
    Django ORM / DB aggregation
          |
          v
       Dashboard

Current scope is request-time, database-backed KPIs. Heavy historical analysis
or statistical workloads should run asynchronously through Celery and may use
Pandas/NumPy without blocking API requests.

Accounting distinction:
    Financial statements are built from posted journals in ``statements.py``.
    This service focuses on operational analytics and rankings.
"""

from decimal import Decimal

from django.db.models import Count, DecimalField, ExpressionWrapper, F, Sum
from django.db.models.functions import Coalesce

from inventory.models import StockBalance
from invoices.models import Invoice, InvoiceItem
from products.models import Product
from purchases.models import Purchase, PurchaseItem

ZERO = Decimal("0.00")
SALES_STATUSES = (Invoice.Status.CONFIRMED, Invoice.Status.PAID)


def _range_filter(queryset, field, date_from=None, date_to=None):
    """Apply optional inclusive date boundaries to a queryset field."""
    if date_from:
        queryset = queryset.filter(**{f"{field}__date__gte": date_from})
    if date_to:
        queryset = queryset.filter(**{f"{field}__date__lte": date_to})
    return queryset


def sales_dashboard(*, date_from=None, date_to=None):
    """Return sales KPIs for the selected date range.

    Metrics include net line sales after invoice-level coupon discounts, sold
    units, and distinct qualifying invoices.
    """
    items = InvoiceItem.objects.filter(invoice__status__in=SALES_STATUSES)
    items = _range_filter(items, "invoice__created_at", date_from, date_to)
    line_total = ExpressionWrapper(
        F("unit_price") * F("quantity"),
        output_field=DecimalField(max_digits=18, decimal_places=2),
    )
    totals = items.aggregate(
        gross_sales=Coalesce(Sum(line_total), ZERO),
        units_sold=Coalesce(Sum("quantity"), 0),
        invoice_count=Count("invoice", distinct=True),
    )
    invoices = Invoice.objects.filter(status__in=SALES_STATUSES)
    invoices = _range_filter(invoices, "created_at", date_from, date_to)
    discount_total = invoices.aggregate(total=Coalesce(Sum("coupon_discount"), ZERO))["total"]
    return {
        "date_from": date_from,
        "date_to": date_to,
        "gross_sales": totals["gross_sales"] - discount_total,
        "units_sold": totals["units_sold"],
        "invoice_count": totals["invoice_count"],
    }


def purchase_dashboard(*, date_from=None, date_to=None):
    """Return purchase value, quantity, and document count for a date range."""
    items = PurchaseItem.objects.filter(purchase__status=Purchase.Status.CONFIRMED)
    items = _range_filter(items, "purchase__created_at", date_from, date_to)
    line_total = ExpressionWrapper(
        F("unit_purchase_price") * F("quantity"),
        output_field=DecimalField(max_digits=18, decimal_places=2),
    )
    totals = items.aggregate(
        purchase_value=Coalesce(Sum(line_total), ZERO),
        units_purchased=Coalesce(Sum("quantity"), 0),
        purchase_count=Count("purchase", distinct=True),
    )
    return {
        "date_from": date_from,
        "date_to": date_to,
        "purchase_value": totals["purchase_value"],
        "units_purchased": totals["units_purchased"],
        "purchase_count": totals["purchase_count"],
    }


def inventory_dashboard(*, low_stock_threshold=10):
    """Return current inventory KPIs and products at/below a stock threshold.

    Inventory value is an operational estimate based on current quantity times
    the product purchase price; it is not the formal accounting valuation.
    """
    stock_rows = (
        Product.objects.filter(is_active=True)
        .values("id", "name", "purchase_price")
        .annotate(stock=Coalesce(Sum("stock_balances__quantity"), 0))
        .order_by("name")
    )
    total_units = sum((row["stock"] for row in stock_rows), 0)
    inventory_value = sum(
        ((row["stock"] or 0) * (row["purchase_price"] or ZERO) for row in stock_rows),
        ZERO,
    )
    low_stock = [
        {"product_id": row["id"], "product_name": row["name"], "stock": row["stock"]}
        for row in stock_rows
        if row["stock"] <= low_stock_threshold
    ]
    return {
        "total_units": total_units,
        "inventory_value": inventory_value,
        "product_count": len(stock_rows),
        "low_stock_threshold": low_stock_threshold,
        "low_stock": low_stock,
        "low_stock_count": len(low_stock),
    }


def top_products(*, date_from=None, date_to=None, limit=10):
    """Return top-selling products ordered by quantity, then revenue."""
    items = InvoiceItem.objects.filter(invoice__status__in=SALES_STATUSES)
    items = _range_filter(items, "invoice__created_at", date_from, date_to)
    line_total = ExpressionWrapper(
        F("unit_price") * F("quantity"),
        output_field=DecimalField(max_digits=18, decimal_places=2),
    )
    rows = (
        items.annotate(line_total=line_total)
        .values("product_id", "product__name")
        .annotate(
            quantity=Coalesce(Sum("quantity"), 0),
            revenue=Coalesce(Sum("line_total"), ZERO),
        )
        .order_by("-quantity", "-revenue", "product_id")[:limit]
    )
    return list(rows)


def sales_by_employee(*, date_from=None, date_to=None):
    """Return sales quantity and revenue grouped by invoice creator."""
    items = InvoiceItem.objects.filter(invoice__status__in=SALES_STATUSES)
    items = _range_filter(items, "invoice__created_at", date_from, date_to)
    line_total = ExpressionWrapper(
        F("unit_price") * F("quantity"),
        output_field=DecimalField(max_digits=18, decimal_places=2),
    )
    rows = (
        items.annotate(line_total=line_total)
        .values("invoice__created_by_id", "invoice__created_by__email")
        .annotate(
            quantity=Coalesce(Sum("quantity"), 0),
            revenue=Coalesce(Sum("line_total"), ZERO),
        )
        .order_by("-revenue", "invoice__created_by_id")
    )
    return list(rows)
