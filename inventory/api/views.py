from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import generics, status
from rest_framework.response import Response

from common.exceptions import InsufficientStock, InvalidBusinessOperation
from common.pagination import StandardPagination
from inventory.api.filters import StockBalanceFilter, StockBatchBalanceFilter, StockMovementFilter
from inventory.api.serializers import StockBalanceSerializer, StockBatchBalanceSerializer, StockLocationSerializer, StockMovementSerializer, TransferInputSerializer
from inventory.models import StockBalance, StockBatchBalance, StockLocation, StockMovement
from inventory.permissions import InventoryApprovedTransferPermission, InventoryReadPermission
from inventory.services.transfer_stock import TransferStock


class LocationListView(generics.ListAPIView):
    serializer_class = StockLocationSerializer
    permission_classes = (InventoryReadPermission,)
    permission_codename = "inventory.view_stocklocation"
    pagination_class = StandardPagination

    def get_queryset(self):
        return StockLocation.objects.visible_to(self.request.user).active()


class StockBalanceListView(generics.ListAPIView):
    serializer_class = StockBalanceSerializer
    permission_classes = (InventoryReadPermission,)
    permission_codename = "inventory.view_stockbalance"
    pagination_class = StandardPagination
    filter_backends = (DjangoFilterBackend,)
    filterset_class = StockBalanceFilter

    def get_queryset(self):
        return (
            StockBalance.objects.select_related("product", "location")
            .filter(location__in=StockLocation.objects.visible_to(self.request.user))
            .order_by("location__name", "product__name")
        )


class StockBatchBalanceListView(generics.ListAPIView):
    serializer_class = StockBatchBalanceSerializer
    permission_classes = (InventoryReadPermission,)
    permission_codename = "inventory.view_stockbalance"
    pagination_class = StandardPagination
    filter_backends = (DjangoFilterBackend,)
    filterset_class = StockBatchBalanceFilter

    def get_queryset(self):
        return (
            StockBatchBalance.objects.select_related("batch__product", "location", "location__site")
            .filter(location__in=StockLocation.objects.visible_to(self.request.user))
            .order_by("batch__expiry_date", "batch__product__name", "location__name")
        )


class MovementListView(generics.ListAPIView):
    serializer_class = StockMovementSerializer
    permission_classes = (InventoryReadPermission,)
    permission_codename = "inventory.view_stockmovement"
    pagination_class = StandardPagination
    filter_backends = (DjangoFilterBackend,)
    filterset_class = StockMovementFilter

    def get_queryset(self):
        return (
            StockMovement.objects.visible_to(self.request.user)
            .prefetch_related("items__product", "items__batch")
            .select_related("source_location", "destination_location", "created_by")
        )


class TransferView(generics.GenericAPIView):
    serializer_class = TransferInputSerializer
    permission_classes = (InventoryApprovedTransferPermission,)

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
        except InsufficientStock as exc:
            return Response({"detail": str(exc), "code": "insufficient_stock"}, status=409)
        except InvalidBusinessOperation as exc:
            return Response({"detail": str(exc), "code": "transfer_invalid"}, status=status.HTTP_409_CONFLICT)

        movement = (
            StockMovement.objects.prefetch_related("items__product", "items__batch")
            .select_related("source_location", "destination_location", "created_by")
            .get(pk=movement.pk)
        )
        return Response(StockMovementSerializer(movement).data, status=status.HTTP_201_CREATED)
