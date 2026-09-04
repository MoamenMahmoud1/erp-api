from adrf import viewsets
from django.db.models import OuterRef, Subquery, Sum, Value
from django.db.models.functions import Coalesce
from rest_framework import filters

from common.pagination import StandardPagination
from common.permissions import ReadAuthenticatedWriteStaffPermission

from products.api.serializers import (
    CartonPricingSerializer,
    ProductSerializer,
)
from products.models import CartonPricing, Product

class ProductViewSet(viewsets.ModelViewSet):
    serializer_class = ProductSerializer
    permission_classes = (
        ReadAuthenticatedWriteStaffPermission,
    )
    pagination_class = StandardPagination

    filter_backends = (
        filters.SearchFilter,
        filters.OrderingFilter,
    )

    search_fields = (
        "name",
    )

    ordering_fields = (
        "name",
        "purchase_price",
        "selling_price",
        "created_at",
        "updated_at",
    )

    ordering = (
        "name",
        "pk",
    )

    def get_queryset(self):
        # Aggregate stock and sold quantities with subqueries so the two sums do
        # not multiply each other across joined rows (a well-known Django join
        # pitfall). Both are read-only — the authoritative stock state lives in
        # inventory.StockBalance.
        sold_subquery = (
            self._confirmed_invoice_item_qty()
        )
        stock_subquery = (
            Product.objects.filter(pk=OuterRef("pk"))
            .values("pk")
            .annotate(total=Sum("stock_balances__quantity"))
            .values("total")
        )
        return (
            Product.objects.annotate(
                _total_stock=Coalesce(Subquery(stock_subquery), Value(0)),
                _sold_quantity=Coalesce(Subquery(sold_subquery), Value(0)),
            )
        )

    @staticmethod
    def _confirmed_invoice_item_qty():
        # Quantity sold on confirmed/paid invoices only. Draft and cancelled
        # invoices are NOT sales.
        from invoices.models import Invoice, InvoiceItem

        return (
            InvoiceItem.objects.filter(
                product=OuterRef("pk"),
                invoice__status__in=(
                    Invoice.Status.CONFIRMED,
                    Invoice.Status.PAID,
                ),
            )
            .values("product")
            .annotate(total=Sum("quantity"))
            .values("total")
        )


class CartonPricingViewSet(viewsets.ModelViewSet):
    serializer_class = CartonPricingSerializer
    permission_classes = (
        ReadAuthenticatedWriteStaffPermission,
    )
    pagination_class = StandardPagination

    filter_backends = (
        filters.SearchFilter,
        filters.OrderingFilter,
    )

    search_fields = (
        "name",
    )

    ordering_fields = (
        "name",
        "units_per_carton",
        "carton_price",
        "created_at",
        "updated_at",
    )

    ordering = (
        "name",
        "pk",
    )

    def get_queryset(self):
        return CartonPricing.objects.all()
