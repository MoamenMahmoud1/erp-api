"""Explainable product-level intelligence derived from ERP transactions."""

from datetime import timedelta
from decimal import Decimal, ROUND_CEILING

from django.db.models import Count, DecimalField, ExpressionWrapper, F, Max, Sum
from django.db.models.functions import Coalesce
from django.utils import timezone

from common.report_cache import cached_report
from inventory.models import StockBalance
from invoices.models import InvoiceItem
from products.models import Product

ZERO = Decimal("0.00")
SALES_STATUSES = ("confirmed", "paid")


def _quantize(value, places="0.01"):
    return Decimal(value).quantize(Decimal(places))


def _ceil_units(value):
    return int(Decimal(value).quantize(Decimal("1"), rounding=ROUND_CEILING))


def _sales_expression(field, fallback):
    return ExpressionWrapper(
        F("quantity") * Coalesce(F(field), F(fallback)),
        output_field=DecimalField(max_digits=20, decimal_places=2),
    )


@cached_report("product_intelligence", timeout=3600)
def product_intelligence(
    *,
    as_of=None,
    lookback_days=30,
    forecast_days=7,
    target_stock_days=14,
    slow_moving_days=60,
    limit=100,
    product_id=None,
):
    """Return explainable demand, stock-health and reorder recommendations.

    This is deliberately a deterministic planning heuristic. It never creates
    purchase orders and does not claim to be a machine-learning forecast.
    """
    if as_of is None:
        as_of = timezone.localdate()

    current_start = as_of - timedelta(days=lookback_days - 1)
    previous_end = current_start - timedelta(days=1)
    previous_start = previous_end - timedelta(days=lookback_days - 1)
    slow_start = as_of - timedelta(days=slow_moving_days - 1)

    products = Product.objects.filter(is_active=True).order_by("name", "pk")
    if product_id is not None:
        products = products.filter(pk=product_id)
    product_rows = list(products.values("id", "name", "category", "purchase_price", "selling_price"))
    if not product_rows:
        return {
            "as_of": as_of.isoformat(),
            "lookback_days": lookback_days,
            "forecast_days": forecast_days,
            "target_stock_days": target_stock_days,
            "summary": {
                "product_count": 0,
                "out_of_stock_count": 0,
                "reorder_count": 0,
                "slow_moving_count": 0,
                "estimated_reorder_units": 0,
            },
            "products": [],
        }

    product_ids = [row["id"] for row in product_rows]
    sale_items = InvoiceItem.objects.filter(
        product_id__in=product_ids,
        invoice__status__in=SALES_STATUSES,
    )
    revenue_expr = ExpressionWrapper(
        F("quantity") * F("unit_price"),
        output_field=DecimalField(max_digits=20, decimal_places=2),
    )
    cogs_expr = _sales_expression("cost_price", "product__purchase_price")

    current = {
        row["product_id"]: row
        for row in sale_items.filter(
            invoice__created_at__date__gte=current_start,
            invoice__created_at__date__lte=as_of,
        )
        .values("product_id")
        .annotate(
            sold_units=Coalesce(Sum("quantity"), 0),
            revenue=Coalesce(Sum(revenue_expr), ZERO),
            cogs=Coalesce(Sum(cogs_expr), ZERO),
            sales_days=Count("invoice__created_at__date", distinct=True),
        )
    }
    previous = {
        row["product_id"]: row
        for row in sale_items.filter(
            invoice__created_at__date__gte=previous_start,
            invoice__created_at__date__lte=previous_end,
        )
        .values("product_id")
        .annotate(sold_units=Coalesce(Sum("quantity"), 0))
    }
    last_sales = {
        row["product_id"]: row["last_sale"]
        for row in sale_items.filter(invoice__created_at__date__gte=slow_start)
        .values("product_id")
        .annotate(last_sale=Max("invoice__created_at"))
    }
    stock = {
        row["product_id"]: row
        for row in StockBalance.objects.filter(product_id__in=product_ids)
        .values("product_id")
        .annotate(
            stock=Coalesce(Sum("quantity"), 0),
            inventory_value=Coalesce(Sum("total_cost"), ZERO),
        )
    }

    items = []
    for product in product_rows:
        pid = product["id"]
        sales = current.get(pid, {})
        previous_sales = previous.get(pid, {})
        stock_row = stock.get(pid, {})

        sold_units = int(sales.get("sold_units", 0) or 0)
        previous_units = int(previous_sales.get("sold_units", 0) or 0)
        revenue = Decimal(sales.get("revenue", ZERO) or ZERO)
        cogs = Decimal(sales.get("cogs", ZERO) or ZERO)
        current_sales_days = int(sales.get("sales_days", 0) or 0)
        stock_units = int(stock_row.get("stock", 0) or 0)
        inventory_value = Decimal(stock_row.get("inventory_value", ZERO) or ZERO)

        average_daily_sales = _quantize(Decimal(sold_units) / Decimal(lookback_days))
        days_of_cover = (
            _quantize(Decimal(stock_units) / average_daily_sales, "0.1")
            if average_daily_sales > 0
            else None
        )
        forecast_units = _ceil_units(average_daily_sales * forecast_days)
        target_units = _ceil_units(average_daily_sales * target_stock_days)
        reorder_units = max(0, target_units - stock_units) if average_daily_sales > 0 else 0

        if previous_units > 0:
            trend_pct = _quantize(
                ((Decimal(sold_units) - Decimal(previous_units)) / Decimal(previous_units)) * Decimal("100")
            )
        elif sold_units > 0:
            trend_pct = Decimal("100.00")
        else:
            trend_pct = Decimal("0.00")

        gross_profit = revenue - cogs
        gross_margin_pct = (
            _quantize((gross_profit / revenue) * Decimal("100"))
            if revenue > 0
            else None
        )

        last_sale = last_sales.get(pid)
        days_since_last_sale = (as_of - last_sale.date()).days if last_sale else None
        slow_moving = sold_units == 0 and stock_units > 0
        if days_since_last_sale is not None and days_since_last_sale >= slow_moving_days:
            slow_moving = True

        if stock_units <= 0:
            stock_status = "out_of_stock"
        elif average_daily_sales > 0 and days_of_cover is not None and days_of_cover <= Decimal(forecast_days):
            stock_status = "reorder"
        elif average_daily_sales == 0:
            stock_status = "no_demand"
        else:
            stock_status = "healthy"

        if sold_units == 0:
            velocity_band = "no_sales"
        elif average_daily_sales >= Decimal("5"):
            velocity_band = "fast"
        elif average_daily_sales >= Decimal("1"):
            velocity_band = "steady"
        else:
            velocity_band = "slow"

        if stock_status == "out_of_stock":
            recommendation = "Reorder immediately if this product is still commercially required."
        elif reorder_units > 0:
            recommendation = f"Consider replenishing about {reorder_units} units to restore {target_stock_days} days of cover."
        elif slow_moving:
            recommendation = "Review pricing, promotion or assortment because stock is moving slowly."
        else:
            recommendation = "No immediate action; continue monitoring demand and stock coverage."

        items.append(
            {
                "product_id": pid,
                "product_name": product["name"],
                "category": product["category"],
                "purchase_price": product["purchase_price"],
                "selling_price": product["selling_price"],
                "stock_units": stock_units,
                "inventory_value": inventory_value,
                "sold_units": sold_units,
                "previous_period_sold_units": previous_units,
                "average_daily_sales": average_daily_sales,
                "forecast_units": forecast_units,
                "days_of_cover": days_of_cover,
                "trend_pct": trend_pct,
                "revenue": revenue,
                "estimated_cogs": cogs,
                "estimated_gross_profit": gross_profit,
                "estimated_gross_margin_pct": gross_margin_pct,
                "sales_days": current_sales_days,
                "last_sale_at": last_sale,
                "days_since_last_sale": days_since_last_sale,
                "velocity_band": velocity_band,
                "stock_status": stock_status,
                "slow_moving": slow_moving,
                "reorder_quantity": reorder_units,
                "recommendation": recommendation,
            }
        )

    status_priority = {"out_of_stock": 0, "reorder": 1, "no_demand": 2, "healthy": 3}
    items.sort(
        key=lambda row: (
            status_priority[row["stock_status"]],
            -row["reorder_quantity"],
            -float(row["revenue"]),
            row["product_name"].lower(),
        )
    )
    limited_items = items[:limit]

    return {
        "as_of": as_of.isoformat(),
        "lookback_days": lookback_days,
        "forecast_days": forecast_days,
        "target_stock_days": target_stock_days,
        "slow_moving_days": slow_moving_days,
        "summary": {
            "product_count": len(items),
            "out_of_stock_count": sum(item["stock_status"] == "out_of_stock" for item in items),
            "reorder_count": sum(item["reorder_quantity"] > 0 for item in items),
            "slow_moving_count": sum(item["slow_moving"] for item in items),
            "estimated_reorder_units": sum(item["reorder_quantity"] for item in items),
        },
        "products": limited_items,
    }
