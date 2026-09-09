"""Fast operational analytics for ERP dashboards."""

from datetime import timedelta
from decimal import Decimal

from django.db.models import Count, DecimalField, ExpressionWrapper, F, Q, Sum
from django.db.models.functions import Coalesce, TruncDate
from django.utils import timezone

from inventory.models import StockBatchBalance
from invoices.models import Invoice, InvoiceItem, InvoiceReturn
from organization.services.metrics import company_master_data_counts
from products.models import Product
from purchases.models import Purchase, PurchaseItem

ZERO = Decimal("0.00")
SALES_STATUSES = (Invoice.Status.CONFIRMED, Invoice.Status.PAID, Invoice.Status.RETURNED)


def _range_filter(queryset, field, date_from=None, date_to=None):
    if date_from:
        queryset = queryset.filter(**{f"{field}__date__gte": date_from})
    if date_to:
        queryset = queryset.filter(**{f"{field}__date__lte": date_to})
    return queryset


def sales_dashboard(*, date_from=None, date_to=None, site_id=None):
    items = InvoiceItem.objects.filter(invoice__status__in=SALES_STATUSES)
    if site_id is not None:
        items = items.filter(invoice__site_id=site_id)
    items = _range_filter(items, "invoice__created_at", date_from, date_to)
    line_total = ExpressionWrapper(F("unit_price") * F("quantity"), output_field=DecimalField(max_digits=18, decimal_places=2))
    totals = items.aggregate(gross_sales=Coalesce(Sum(line_total), ZERO), units_sold=Coalesce(Sum("quantity"), 0), invoice_count=Count("invoice", distinct=True))
    invoices = Invoice.objects.filter(status__in=SALES_STATUSES)
    if site_id is not None:
        invoices = invoices.filter(site_id=site_id)
    invoices = _range_filter(invoices, "created_at", date_from, date_to)
    discount_total = invoices.aggregate(total=Coalesce(Sum("coupon_discount"), ZERO))["total"]
    returns = InvoiceReturn.objects.all()
    if site_id is not None:
        returns = returns.filter(site_id=site_id)
    returns = _range_filter(returns, "created_at", date_from, date_to)
    return_totals = returns.aggregate(amount=Coalesce(Sum("refund_amount"), ZERO))
    return_items = returns.values("id").annotate(returned_units=Coalesce(Sum("items__quantity"), 0))
    returned_units = sum((row["returned_units"] for row in return_items), 0)
    daily_gross = items.annotate(day=TruncDate("invoice__created_at")).values("day").annotate(value=Coalesce(Sum(line_total), ZERO)).order_by("day")
    daily_discounts = {row["day"]: row["value"] for row in invoices.annotate(day=TruncDate("created_at")).values("day").annotate(value=Coalesce(Sum("coupon_discount"), ZERO))}
    daily_returns = {row["day"]: row["value"] for row in returns.annotate(day=TruncDate("created_at")).values("day").annotate(value=Coalesce(Sum("refund_amount"), ZERO))}
    gross_by_day = {row["day"]: row["value"] for row in daily_gross}
    trend_dates = set(daily_discounts) | set(daily_returns) | set(gross_by_day)
    trend = [{"date": day.isoformat(), "value": gross_by_day.get(day, ZERO) - daily_discounts.get(day, ZERO) - daily_returns.get(day, ZERO)} for day in sorted(trend_dates)]
    return {"date_from": date_from, "date_to": date_to, "site_id": site_id, "gross_sales": totals["gross_sales"] - discount_total - return_totals["amount"], "units_sold": totals["units_sold"] - returned_units, "invoice_count": totals["invoice_count"], "returns": return_totals["amount"], "returned_units": returned_units, "trend": trend}


def purchase_dashboard(*, date_from=None, date_to=None, site_id=None):
    items = PurchaseItem.objects.filter(purchase__status=Purchase.Status.CONFIRMED)
    if site_id is not None:
        items = items.filter(purchase__site_id=site_id)
    items = _range_filter(items, "purchase__created_at", date_from, date_to)
    line_total = ExpressionWrapper(F("unit_purchase_price") * F("quantity"), output_field=DecimalField(max_digits=18, decimal_places=2))
    totals = items.aggregate(purchase_value=Coalesce(Sum(line_total), ZERO), units_purchased=Coalesce(Sum("quantity"), 0), purchase_count=Count("purchase", distinct=True))
    daily = items.annotate(day=TruncDate("purchase__created_at")).values("day").annotate(value=Coalesce(Sum(line_total), ZERO)).order_by("day")
    return {"date_from": date_from, "date_to": date_to, "site_id": site_id, "purchase_value": totals["purchase_value"], "units_purchased": totals["units_purchased"], "purchase_count": totals["purchase_count"], "trend": [{"date": row["day"].isoformat(), "value": row["value"]} for row in daily]}


def inventory_dashboard(*, low_stock_threshold=10, site_id=None):
    products = Product.objects.filter(is_active=True)
    stock_filter = Q(stock_balances__location__site_id=site_id) if site_id is not None else Q()
    stock_rows = list(
        products.values("id", "name")
        .annotate(
            stock=Coalesce(Sum("stock_balances__quantity", filter=stock_filter), 0),
            inventory_value=Coalesce(Sum("stock_balances__total_cost", filter=stock_filter), ZERO),
        )
        .order_by("name")
    )
    # A site filter on the aggregation, rather than only on Product, prevents stock from other branches being included.
    if site_id is not None:
        stock_rows = [row for row in stock_rows if row["stock"] or row["inventory_value"]]
    total_units = sum((row["stock"] for row in stock_rows), 0)
    inventory_value = sum((row["inventory_value"] for row in stock_rows), ZERO)
    low_stock = [{"product_id": row["id"], "product_name": row["name"], "stock": row["stock"]} for row in stock_rows if row["stock"] <= low_stock_threshold]
    batch_queryset = StockBatchBalance.objects.filter(quantity__gt=0, batch__product__is_active=True)
    if site_id is not None:
        batch_queryset = batch_queryset.filter(location__site_id=site_id)
    today = timezone.localdate()
    expiry_rows = list(batch_queryset.select_related("location", "batch__product").filter(batch__expiry_date__isnull=False).order_by("batch__expiry_date", "batch_id"))
    expired_rows = [row for row in expiry_rows if row.batch.expiry_date < today]
    expiring_7_rows = [row for row in expiry_rows if today <= row.batch.expiry_date <= today + timedelta(days=7)]
    expiring_30_rows = [row for row in expiry_rows if today <= row.batch.expiry_date <= today + timedelta(days=30)]

    def expiry_item(row):
        return {"product_id": row.batch.product_id, "product_name": row.batch.product.name, "location_id": row.location_id, "location_name": row.location.name, "batch_id": row.batch_id, "batch_number": row.batch.batch_number, "manufactured_date": row.batch.manufactured_date, "expiry_date": row.batch.expiry_date, "days_to_expiry": (row.batch.expiry_date - today).days, "quantity": row.quantity, "inventory_value": row.total_cost}

    return {"site_id": site_id, "total_units": total_units, "inventory_value": inventory_value, "product_count": len(stock_rows), "low_stock_threshold": low_stock_threshold, "low_stock": low_stock, "low_stock_count": len(low_stock), "expired_units": sum((row.quantity for row in expired_rows), 0), "expiring_7_days_units": sum((row.quantity for row in expiring_7_rows), 0), "expiring_30_days_units": sum((row.quantity for row in expiring_30_rows), 0), "expired_batch_count": len(expired_rows), "expiring_7_days_batch_count": len(expiring_7_rows), "expiring_30_days_batch_count": len(expiring_30_rows), "expiry_alerts": [expiry_item(row) for row in expiring_30_rows[:12]], "expired_alerts": [expiry_item(row) for row in expired_rows[:12]]}


def top_products(*, date_from=None, date_to=None, limit=10, site_id=None):
    items = InvoiceItem.objects.filter(invoice__status__in=SALES_STATUSES)
    if site_id is not None:
        items = items.filter(invoice__site_id=site_id)
    items = _range_filter(items, "invoice__created_at", date_from, date_to)
    line_total = ExpressionWrapper(F("unit_price") * F("quantity"), output_field=DecimalField(max_digits=18, decimal_places=2))
    rows = items.annotate(line_total=line_total).values("product_id", "product__name").annotate(quantity=Coalesce(Sum("quantity"), 0), revenue=Coalesce(Sum("line_total"), ZERO)).order_by("-quantity", "-revenue", "product_id")[:limit]
    return list(rows)


def sales_by_employee(*, date_from=None, date_to=None, site_id=None):
    items = InvoiceItem.objects.filter(invoice__status__in=SALES_STATUSES)
    if site_id is not None:
        items = items.filter(invoice__site_id=site_id)
    items = _range_filter(items, "invoice__created_at", date_from, date_to)
    line_total = ExpressionWrapper(F("unit_price") * F("quantity"), output_field=DecimalField(max_digits=18, decimal_places=2))
    rows = items.annotate(line_total=line_total).values("invoice__created_by_id", "invoice__created_by__email", "invoice__created_by__first_name", "invoice__created_by__last_name").annotate(quantity=Coalesce(Sum("quantity"), 0), revenue=Coalesce(Sum("line_total"), ZERO)).order_by("-revenue", "invoice__created_by_id")
    return [{**row, "employee_name": (f"{row['invoice__created_by__first_name']} {row['invoice__created_by__last_name']}").strip() or row["invoice__created_by__email"]} for row in rows]


def customer_sales_ranking(*, date_from=None, date_to=None, limit=5, site_id=None):
    items = InvoiceItem.objects.filter(invoice__status__in=SALES_STATUSES)
    if site_id is not None:
        items = items.filter(invoice__site_id=site_id)
    items = _range_filter(items, "invoice__created_at", date_from, date_to)
    line_total = ExpressionWrapper(F("unit_price") * F("quantity"), output_field=DecimalField(max_digits=18, decimal_places=2))
    sales_rows = list(items.values("invoice__customer_id", "invoice__customer__name").annotate(quantity=Coalesce(Sum("quantity"), 0), gross_revenue=Coalesce(Sum(line_total), ZERO), invoice_count=Count("invoice", distinct=True)).order_by("invoice__customer_id"))
    return_queryset = InvoiceReturn.objects.all()
    if site_id is not None:
        return_queryset = return_queryset.filter(site_id=site_id)
    return_queryset = _range_filter(return_queryset, "created_at", date_from, date_to)
    return_rows = return_queryset.values("invoice__customer_id").annotate(returns=Coalesce(Sum("refund_amount"), ZERO))
    return_map = {row["invoice__customer_id"]: row["returns"] for row in return_rows}
    ranked = []
    for row in sales_rows:
        returns = return_map.get(row["invoice__customer_id"], ZERO)
        ranked.append({"customer_id": row["invoice__customer_id"], "customer_name": row["invoice__customer__name"], "invoice_count": row["invoice_count"], "units_sold": row["quantity"], "gross_revenue": row["gross_revenue"], "returns": returns, "revenue": row["gross_revenue"] - returns})
    ranked.sort(key=lambda row: (-row["revenue"], -row["units_sold"], row["customer_id"]))
    return ranked[:limit], sorted(ranked, key=lambda row: (row["revenue"], row["units_sold"], row["customer_id"]))[:limit]


def dashboard_overview(*, date_from=None, date_to=None, site_id=None):
    from accounting.services.balances import customer_balances, supplier_balances
    from accounting.services.journal import get_default_company
    from accounting.services.statements import cash_flow, profit_and_loss

    company = get_default_company()
    top_customers, bottom_customers = customer_sales_ranking(date_from=date_from, date_to=date_to, limit=5, site_id=site_id)
    return {"counts": company_master_data_counts(), "site_id": site_id, "sales": sales_dashboard(date_from=date_from, date_to=date_to, site_id=site_id), "purchases": purchase_dashboard(date_from=date_from, date_to=date_to, site_id=site_id), "inventory": inventory_dashboard(site_id=site_id), "pnl": profit_and_loss(date_from=date_from, date_to=date_to, company=company), "cash_flow": cash_flow(date_from=date_from, date_to=date_to, company=company), "top_products": top_products(date_from=date_from, date_to=date_to, limit=6, site_id=site_id), "sales_by_employee": sales_by_employee(date_from=date_from, date_to=date_to, site_id=site_id), "top_customers": top_customers, "bottom_customers": bottom_customers, "customer_balances": customer_balances(as_of=date_to), "supplier_balances": supplier_balances(as_of=date_to)}
