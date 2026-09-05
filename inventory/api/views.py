from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import generics, status
from rest_framework.response import Response

from common.exceptions import InvalidBusinessOperation
from common.pagination import StandardPagination
from inventory.api.filters import StockBalanceFilter, StockMovementFilter
from inventory.api.serializers import (
    StockBalanceSerializer,
    StockLocationSerializer,
    StockMovementSerializer,
    TransferInputSerializer,
)
from inventory.models import StockBalance, StockLocation, StockMovement
from inventory.permissions import InventoryReadPermission, InventoryTransferPermission
from inventory.services.transfer_stock import TransferStock


class LocationListView(generics.ListAPIView):
    serializer_class = StockLocationSerializer
    permission_classes = (InventoryReadPermission,)
    pagination_class = StandardPagination

    def get_queryset(self):
        return StockLocation.objects.visible_to(self.request.user).active()


class StockBalanceListView(generics.ListAPIView):
    serializer_class = StockBalanceSerializer
    permission_classes = (InventoryReadPermission,)
    pagination_class = StandardPagination
    filter_backends = (DjangoFilterBackend,)
    filterset_class = StockBalanceFilter

    def get_queryset(self):
        return (
            StockBalance.objects.select_related("product", "location")
            .filter(location__in=StockLocation.objects.visible_to(self.request.user))
            .order_by("location__name", "product__name")
        )


class MovementListView(generics.ListAPIView):
    serializer_class = StockMovementSerializer
    permission_classes = (InventoryReadPermission,)
    pagination_class = StandardPagination
    filter_backends = (DjangoFilterBackend,)
    filterset_class = StockMovementFilter

    def get_queryset(self):
        return (
            StockMovement.objects.visible_to(self.request.user)
            .prefetch_related("items__product")
            .select_related("source_location", "destination_location", "created_by")
        )


class TransferView(generics.GenericAPIView):
    serializer_class = TransferInputSerializer
    permission_classes = (InventoryTransferPermission,)

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        try:
            movement = TransferStock()(
                source_id=data["source_location"],
                destination_id=data["destination_location"],
                items=data["items"],
                created_by=request.user,
                reference=data.get("reference", ""),
            )
        except InvalidBusinessOperation as exc:
            return Response(
                {"detail": str(exc), "code": "transfer_invalid"},
                status=status.HTTP_409_CONFLICT,
            )

        movement = (
            StockMovement.objects.prefetch_related("items__product")
            .select_related("source_location", "destination_location", "created_by")
            .get(pk=movement.pk)
        )
        return Response(StockMovementSerializer(movement).data, status=status.HTTP_201_CREATED)
