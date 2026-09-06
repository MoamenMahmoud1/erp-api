"""
ERP Analytics Service
=====================

Purpose
-------
Provide fast operational KPIs and grouped analytics for dashboards.

Current scope
-------------
The service is intentionally based on Django ORM/database aggregation for
small, request-time reports.  Heavy analysis (large historical datasets,
forecasting, segmentation, anomaly detection, and similar workloads) should
later run through Celery workers and can use Pandas/NumPy without blocking API
requests.

Architecture
------------

    ERP tables
       |
       +---- Invoices ------+
       |                    |
       +---- Purchases -----+----> Django ORM / DB aggregation
       |                    |
       +---- Inventory -----+             |
       |                                  v
       +---- Employees -----+        Dashboard KPIs

Future heavy path:

    API -> Analytics Job -> Celery -> Pandas/NumPy -> Stored Result -> API

Design note
-----------
Analytics reads operational data.  Accounting statements remain responsible
for financial reporting derived from posted journal entries.
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
    """
    Apply optional inclusive date boundaries to a queryset field.

    This helper keeps the date-range behavior consistent across analytics
    functions and avoids repeating the same filtering logic.

    Args:
        queryset: Django queryset to filter.
        field: datetime field path used for the report.
        date_from: optional inclusive lower date.
        date_to: optional inclusive upper date.

    Returns:
        QuerySet: the filtered queryset.
    """
    if date_from:
        queryset = queryset.filter(**{f"{field}__date__gte": date_from})
    if date_to:
        queryset = queryset.filter(**{f"{field}__date__lte": date_to})
    return queryset


def sales_dashboard(*, date_from=None, date_to=None):
    """
    Return high-level sales KPIs for an optional date range.

    Metrics:
        - gross_sales: line sales less invoice-level coupon discounts.
        - units_sold: total quantity on qualifying sales invoices.
        - invoice_count: distinct qualifying invoices.

    The current implementation treats CONFIRMED and PAID invoices as active
    sales records for dashboard purposes.

    Returns:
        dict: date range plus sales KPIs.
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
    """
    Return high-level purchase KPIs for an optional date range.

    Metrics:
        - purchase_value: purchase line value.
        - units_purchased: total purchased quantity.
        - purchase_count: distinct confirmed purchases.

    Returns:
        dict: date range plus purchase KPIs.
    """
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
    """
    Return current inventory KPIs and products at or below a stock threshold.

    Inventory value is calculated from current quantity multiplied by the
    product purchase price.  This is an operational valuation for the
    dashboard; formal financial inventory valuation remains an accounting
    concern.

    Args:
        low_stock_threshold: inclusive quantity threshold for the low-stock
            list.

    Returns:
        dict: total units, inventory value, active product count, and low-stock
        details.
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
    """
    Return the highest-selling products for an optional date range.

    Results are ordered primarily by sold quantity and then by revenue.  The
    report is intentionally a ranking query, not a profitability statement.

    Args:
        date_from/date_to: optional inclusive date range.
        limit: maximum number of products to return.

    Returns:
        list[dict]: grouped product quantity and revenue rows.
    """
    items = InvoiceItem.objects.filter(invoice__status__in=SALES_STATUSES)
    items = _range_filter(items, "invoice__created_at", date_from, date_to)
    line_total = ExpressionWrapper(
        F("unit_price") * F("quantity"),
        output_field=DecimalField(max_digits=18, decimal_places=2),
    )
    rows = (
        items.values("product_id", "product__name")
        .annotate(quantity=Coalesce(Sum("quantity"), 0), revenue=Coalesce(Sum(line_total), ZERO))
        .order_by("-quantity", "-revenue", "product_id")[:limit]
    )
    return list(rows)


def sales_by_employee(*, date_from=None, date_to=None):
    """
    Group sales quantity and revenue by the employee who created each invoice.

    Args:
        date_from/date_to: optional inclusive date range.

    Returns:
        list[dict]: employee identifiers, email addresses, sold quantity, and
        revenue ordered by revenue descending.
    """
    items = InvoiceItem.objects.filter(invoice__status__in=SALES_STATUSES)
    items = _range_filter(items, "invoice__created_at", date_from, date_to)
    line_total = ExpressionWrapper(
        F("unit_price") * F("quantity"),
        output_field=DecimalField(max_digits=18, decimal_places=2),
    )
    rows = (
        items.values("invoice__created_by_id", "invoice__created_by__email")
        .annotate(quantity=Coalesce(Sum("quantity"), 0), revenue=Coalesce(Sum(line_total), ZERO))
        .order_by("-revenue", "invoice__created_by_id")
    )
    return list(rows)
