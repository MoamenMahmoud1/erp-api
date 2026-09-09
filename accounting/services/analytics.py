"""Fast operational analytics for ERP dashboards."""

from decimal import Decimal

from django.db.models import Count, DecimalField, ExpressionWrapper, F, Q, Sum
from django.db.models.functions import Coalesce, TruncDate

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
    if site_id:
        items = items.filter(invoice__site_id=site_id)
    items = _range_filter(items, "invoice__created_at", date_from, date_to)
    line_total = ExpressionWrapper(F("unit_price") * F("quantity"), output_field=DecimalField(max_digits=18, decimal_places=2))
    totals = items.aggregate(gross_sales=Coalesce(Sum(line_total), ZERO), units_sold=Coalesce(Sum("quantity"), 0), invoice_count=Count("invoice", distinct=True))

    invoices = Invoice.objects.filter(status__in=SALES_STATUSES)
    if site_id:
        invoices = invoices.filter(site_id=site_id)
    invoices = _range_filter(invoices, "created_at", date_from, date_to)
    discount_total = invoices.aggregate(total=Coalesce(Sum("coupon_discount"), ZERO))["total"]

    returns = InvoiceReturn.objects.all()
    if site_id:
        returns = returns.filter(invoice__site_id=site_id)
    returns = _range_filter(returns, "created_at", date_from, date_to)
    return_totals = returns.aggregate(amount=Coalesce(Sum("refund_amount"), ZERO))
    returned_units = sum((row["returned_units"] for row in returns.values("id").annotate(returned_units=Coalesce(Sum("items__quantity"), 0))), 0)

    daily_gross = items.annotate(day=TruncDate("invoice__created_at")).values("day").annotate(value=Coalesce(Sum(line_total), ZERO)).order_by("day")
    daily_discounts = {row["day"]: row["value"] for row in invoices.annotate(day=TruncDate("created_at")).values("day").annotate(value=Coalesce(Sum("coupon_discount"), ZERO))}
    daily_returns = {row["day"]: row["value"] for row in returns.annotate(day=TruncDate("created_at")).values("day").annotate(value=Coalesce(Sum("refund_amount"), ZERO))}
    gross_by_day = {row["day"]: row["value"] for row in daily_gross}
    trend = [{"date": day.isoformat(), "value": gross_by_day.get(day, ZERO) - daily_discounts.get(day, ZERO) - daily_returns.get(day, ZERO)} for day in sorted(set(gross_by_day) | set(daily_discounts) | set(daily_returns))]

    return {"date_from": date_from, "date_to": date_to, "site_id": site_id, "gross_sales": totals["gross_sales"] - discount_total - return_totals["amount"], "units_sold": totals["units_sold"] - returned_units, "invoice_count": totals["invoice_count"], "returns": return_totals["amount"], "returned_units": returned_units, "trend": trend}


def purchase_dashboard(*, date_from=None, date_to=None, site_id=None):
    items = PurchaseItem.objects.filter(purchase__status=Purchase.Status.CONFIRMED)
    if site_id:
        items = items.filter(purchase__site_id=site_id)
    items = _range_filter(items, "purchase__created_at", date_from, date_to)
    line_total = ExpressionWrapper(F("unit_purchase_price") * F("quantity"), output_field=DecimalField(max_digits=18, decimal_places=2))
    totals = items.aggregate(purchase_value=Coalesce(Sum(line_total), ZERO), units_purchased=Coalesce(Sum("quantity"), 0), purchase_count=Count("purchase", distinct=True))
    daily = items.annotate(day=TruncDate("purchase__created_at")).values("day").annotate(value=Coalesce(Sum(line_total), ZERO)).order_by("day")
    return {"date_from": date_from, "date_to": date_to, "site_id": site_id, "purchase_value": totals["purchase_value"], "units_purchased": totals["units_purchased"], "purchase_count": totals["purchase_count"], "trend": [{"date": row["day"].isoformat(), "value": row["value"]} for row in daily]}


def inventory_dashboard(*, low_stock_threshold=10, site_id=None):
    products = Product.objects.filter(is_active=True)
    stock_filter = Q(stock_balances__location__site_id=site_id) if site_id else Q()
    stock_rows = products.values("id", "name").annotate(
        stock=Coalesce(Sum("stock_balances__quantity", filter=stock_filter), 0),
        inventory_value=Coalesce(Sum("stock_balances__total_cost", filter=stock_filter), ZERO),
    ).order_by("name")
    total_units = sum((row["stock"] for row in stock_rows), 0)
    inventory_value = sum((row["inventory_value"] for row in stock_rows), ZERO)
    low_stock = [{"product_id": row["id"], "product_name": row["name"], "stock": row["stock"]} for row in stock_rows if row["stock"] <= low_stock_threshold]
    return {"site_id": site_id, "total_units": total_units, "inventory_value": inventory_value, "product_count": len(stock_rows), "low_stock_threshold": low_stock_threshold, "low_stock": low_stock, "low_stock_count": len(low_stock)}


def top_products(*, date_from=None, date_to=None, limit=10, site_id=None):
    items = InvoiceItem.objects.filter(invoice__status__in=SALES_STATUSES)
    if site_id:
        items = items.filter(invoice__site_id=site_id)
    items = _range_filter(items, "invoice__created_at", date_from, date_to)
    line_total = ExpressionWrapper(F("unit_price") * F("quantity"), output_field=DecimalField(max_digits=18, decimal_places=2))
    return list(items.annotate(line_total=line_total).values("product_id", "product__name").annotate(quantity=Coalesce(Sum("quantity"), 0), revenue=Coalesce(Sum("line_total"), ZERO)).order_by("-quantity", "-revenue", "product_id")[:limit])


def sales_by_employee(*, date_from=None, date_to=None, site_id=None):
    items = InvoiceItem.objects.filter(invoice__status__in=SALES_STATUSES)
    if site_id:
        items = items.filter(invoice__site_id=site_id)
    items = _range_filter(items, "invoice__created_at", date_from, date_to)
    line_total = ExpressionWrapper(F("unit_price") * F("quantity"), output_field=DecimalField(max_digits=18, decimal_places=2))
    rows = items.annotate(line_total=line_total).values("invoice__created_by_id", "invoice__created_by__email", "invoice__created_by__first_name", "invoice__created_by__last_name").annotate(quantity=Coalesce(Sum("quantity"), 0), revenue=Coalesce(Sum("line_total"), ZERO)).order_by("-revenue", "invoice__created_by_id")
    return [{**row, "employee_name": (f"{row['invoice__created_by__first_name']} {row['invoice__created_by__last_name']}".strip() or row["invoice__created_by__email"])} for row in rows]


def dashboard_overview(*, date_from=None, date_to=None, site_id=None):
    from accounting.services.balances import customer_balances, supplier_balances
    from accounting.services.journal import get_default_company
    from accounting.services.statements import cash_flow, profit_and_loss

    company = get_default_company()
    return {"counts": company_master_data_counts(), "site_id": site_id, "sales": sales_dashboard(date_from=date_from, date_to=date_to, site_id=site_id), "purchases": purchase_dashboard(date_from=date_from, date_to=date_to, site_id=site_id), "inventory": inventory_dashboard(site_id=site_id), "pnl": profit_and_loss(date_from=date_from, date_to=date_to, company=company), "cash_flow": cash_flow(date_from=date_from, date_to=date_to, company=company), "top_products": top_products(date_from=date_from, date_to=date_to, limit=6, site_id=site_id), "sales_by_employee": sales_by_employee(date_from=date_from, date_to=date_to, site_id=site_id), "customer_balances": customer_balances(as_of=date_to), "supplier_balances": supplier_balances(as_of=date_to)}
