from django.db.models import OuterRef, Subquery, Sum, Value
from django.db.models.functions import Coalesce
from rest_framework import filters, viewsets

from common.pagination import StandardPagination
from common.permissions import ReadAuthenticatedWriteStaffPermission
from invoices.models import Invoice, InvoiceItem
from products.api.serializers import CartonPricingSerializer, ProductSerializer
from products.models import CartonPricing, Product


class ProductViewSet(viewsets.ModelViewSet):
    serializer_class = ProductSerializer
    permission_classes = (ReadAuthenticatedWriteStaffPermission,)
    pagination_class = StandardPagination

    filter_backends = (
        filters.SearchFilter,
        filters.OrderingFilter,
    )
    search_fields = ("name",)
    ordering_fields = (
        "name",
        "purchase_price",
        "selling_price",
        "created_at",
        "updated_at",
    )
    ordering = ("name", "pk")

    def get_queryset(self):
        sold_subquery = (
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
        stock_subquery = (
            Product.objects.filter(pk=OuterRef("pk"))
            .values("pk")
            .annotate(total=Sum("stock_balances__quantity"))
            .values("total")
        )
        return Product.objects.annotate(
            _total_stock=Coalesce(Subquery(stock_subquery), Value(0)),
            _sold_quantity=Coalesce(Subquery(sold_subquery), Value(0)),
        )


class CartonPricingViewSet(viewsets.ModelViewSet):
    serializer_class = CartonPricingSerializer
    permission_classes = (ReadAuthenticatedWriteStaffPermission,)
    pagination_class = StandardPagination

    filter_backends = (
        filters.SearchFilter,
        filters.OrderingFilter,
    )
    search_fields = ("name",)
    ordering_fields = (
        "name",
        "units_per_carton",
        "carton_price",
        "created_at",
        "updated_at",
    )
    ordering = ("name", "pk")

    def get_queryset(self):
        return CartonPricing.objects.all()
