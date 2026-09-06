from datetime import date
from decimal import Decimal

from django.db.models import DecimalField, ExpressionWrapper, F, IntegerField, Sum
from django.db.models.functions import Coalesce

from accounting.services.journal import get_default_company
from inventory.models import StockBalance
from invoices.models import InvoiceItem
from purchases.models import Purchase, PurchaseItem

ZERO = Decimal("0.00")
SALES_STATUSES = ("confirmed", "paid", "returned")


def _range_filter(queryset, field, date_from=None, date_to=None):
    if date_from:
        queryset = queryset.filter(**{f"{field}__date__gte": date_from})
    if date_to:
        queryset = queryset.filter(**{f"{field}__date__lte": date_to})
    return queryset


def sales_dashboard(*, date_from=None, date_to=None):
    invoices = InvoiceItem.objects.filter(invoice__status__in=SALES_STATUSES)
    invoices = _range_filter(invoices, "invoice__created_at", date_from, date_to)
    line_total = ExpressionWrapper(
        F("unit_price") * F("quantity"),
        output_field=DecimalField(max_digits=18, decimal_places=2),
    )
    totals = invoices.aggregate(
        gross_sales=Coalesce(Sum(line_total), ZERO),
        units_sold=Coalesce(Sum("quantity"), 0),
        invoice_count=Coalesce(Sum("invoice_id", distinct=True), 0),
    )
    discounts = invoices.values("invoice_id").annotate(
        discount=F("invoice__coupon_discount")
    )
    discount_total = sum((row["discount"] or ZERO for row in discounts), ZERO)
    returns = invoices.filter(invoice__status=InvoiceItem._meta.model._meta.get_field("invoice").remote_field.model.Status.RETURNED).aggregate(
        returned_units=Coalesce(Sum("quantity"), 0),
    )["returned_units"] or 0
    return {
        "date_from": date_from,
        "date_to": date_to,
        "gross_sales": totals["gross_sales"] - discount_total,
        "units_sold": totals["units_sold"] - returns,
        "invoice_count": totals["invoice_count"],
    }


def purchase_dashboard(*, date_from=None, date_to=None):
    purchases = PurchaseItem.objects.filter(purchase__status=Purchase.Status.CONFIRMED)
    purchases = _range_filter(purchases, "purchase__created_at", date_from, date_to)
    line_total = ExpressionWrapper(
        F("unit_purchase_price") * F("quantity"),
        output_field=DecimalField(max_digits=18, decimal_places=2),
    )
    totals = purchases.aggregate(
        purchase_value=Coalesce(Sum(line_total), ZERO),
        units_purchased=Coalesce(Sum("quantity"), 0),
        purchase_count=Coalesce(Sum("purchase_id", distinct=True), 0),
    )
    return {
        "date_from": date_from,
        "date_to": date_to,
        "purchase_value": totals["purchase_value"],
        "units_purchased": totals["units_purchased"],
        "purchase_count": totals["purchase_count"],
    }


def inventory_dashboard(*, low_stock_threshold=10, top_n=10):
    stock_rows = (
        StockBalance.objects.values("product_id", "product__name", "product__purchase_price")
        .annotate(stock=Coalesce(Sum("quantity"), 0))
        .order_by("product__name")
    )
    total_units = sum((row["stock"] for row in stock_rows), 0)
    inventory_value = sum(
        ((row["stock"] or 0) * (row["product__purchase_price"] or ZERO) for row in stock_rows),
        ZERO,
    )
    low_stock = [
        {
            "product_id": row["product_id"],
            "product_name": row["product__name"],
            "stock": row["stock"],
        }
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
        "top_n": top_n,
    }


def top_products(*, date_from=None, date_to=None, limit=10):
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
