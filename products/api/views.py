from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, viewsets

from common.pagination import StandardPagination
from common.permissions import ReadAuthenticatedWriteStaffPermission
from products.api.serializers import CartonPricingSerializer, ProductSerializer
from products.models import CartonPricing, Product


class ProductViewSet(viewsets.ModelViewSet):
    serializer_class = ProductSerializer
    permission_classes = (ReadAuthenticatedWriteStaffPermission,)
    pagination_class = StandardPagination
    filter_backends = (DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter)
    filterset_fields = ("is_active", "category")
    search_fields = ("name", "category")
    ordering_fields = ("name", "purchase_price", "selling_price", "created_at", "updated_at")
    ordering = ("name", "pk")

    def get_queryset(self):
        return Product.objects.with_stock_stats()


class CartonPricingViewSet(viewsets.ModelViewSet):
    serializer_class = CartonPricingSerializer
    permission_classes = (ReadAuthenticatedWriteStaffPermission,)
    pagination_class = StandardPagination
    filter_backends = (DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter)
    filterset_fields = ("product",)
    search_fields = ("name", "product__name")
    ordering_fields = ("name", "units_per_carton", "carton_price", "created_at", "updated_at")
    ordering = ("name", "pk")

    def get_queryset(self):
        return CartonPricing.objects.select_related("product")
