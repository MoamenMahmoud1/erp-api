"""Read-only inventory access helpers.

These are the canonical way to read stock. ``inventory.StockBalance`` is the
single authoritative current-stock state; nothing else in the codebase should
compute "current stock" from first principles.
"""

from django.db.models import Sum

from inventory.models import StockBalance


def get_stock(product, location):
    """Current on-hand quantity for ``product`` at ``location`` (0 if none)."""
    return (
        StockBalance.objects.filter(
            product=product,
            location=location,
        ).values("quantity").first()
        or {"quantity": 0}
    )["quantity"]


def get_total_stock(product):
    """Aggregated current on-hand quantity across every StockLocation."""
    return (
        StockBalance.objects.filter(product=product).aggregate(
            total=Sum("quantity")
        )["total"]
        or 0
    )


def get_available_stock(product, location):
    """Quantity available for a new sale/transfer at ``location``.

    Stock is only released when an invoice is confirmed (a SALE movement), so the
    current balance at a location is the available quantity there.
    """
    return get_stock(product, location)


__all__ = ("get_stock", "get_total_stock", "get_available_stock")