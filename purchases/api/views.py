from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, generics, status
from rest_framework.response import Response

from authentication.throttling import SensitiveActionThrottle
from common.pagination import StandardPagination
from purchases.api.filters.purchase import PurchaseFilter
from purchases.api.serializers import (
    PurchaseListSerializer,
    PurchaseReturnInputSerializer,
    PurchaseReturnSerializer,
    PurchaseSerializer,
)
from purchases.models import Purchase
from purchases.permissions.purchase import PurchaseAccessPermission
from purchases.services.cancel_purchase import CancelPurchaseService
from purchases.services.confirm_purchase import ConfirmPurchaseService
from purchases.services.draft import CreatePurchase, DeletePurchase, UpdatePurchase
from purchases.services.return_purchase import ReturnPurchase


class PurchaseListCreateView(generics.ListCreateAPIView):
    permission_classes = (PurchaseAccessPermission,)
    pagination_class = StandardPagination
    filter_backends = (DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter)
    filterset_class = PurchaseFilter
    search_fields = ("reference", "supplier__name")
    ordering_fields = ("created_at", "updated_at", "status")
    ordering = ("-created_at",)

    def get_queryset(self):
        return Purchase.objects.with_purchase_data().visible_to(self.request.user)

    def get_serializer_class(self):
        return PurchaseListSerializer if self.request.method == "GET" else PurchaseSerializer

    def perform_create(self, serializer):
        self.created_purchase = CreatePurchase()(
            created_by=self.request.user,
            validated_data=serializer.validated_data,
        )

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            purchase = CreatePurchase()(created_by=request.user, validated_data=serializer.validated_data)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=400)
        return Response(PurchaseSerializer(purchase).data, status=201)


class PurchaseDetailView(generics.RetrieveAPIView):
    permission_classes = (PurchaseAccessPermission,)
    serializer_class = PurchaseSerializer

    def get_queryset(self):
        return Purchase.objects.with_purchase_data().visible_to(self.request.user)


class PurchaseUpdateView(generics.UpdateAPIView):
    permission_classes = (PurchaseAccessPermission,)
    serializer_class = PurchaseSerializer

    def get_queryset(self):
        return Purchase.objects.visible_to(self.request.user)

    def update(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data, partial=kwargs.pop("partial", False))
        serializer.is_valid(raise_exception=True)
        try:
            purchase = UpdatePurchase()(purchase_id=kwargs["pk"], validated_data=serializer.validated_data)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=409)
        return Response(PurchaseSerializer(purchase).data)


class PurchaseConfirmView(generics.GenericAPIView):
    permission_classes = (PurchaseAccessPermission,)
    permission_codename = "purchases.confirm_purchase"
    throttle_classes = (SensitiveActionThrottle,)
    serializer_class = PurchaseSerializer

    def post(self, request, pk):
        try:
            purchase = ConfirmPurchaseService.execute(purchase_id=pk, created_by_id=request.user.pk)
        except Purchase.DoesNotExist:
            return Response({"detail": "Purchase not found."}, status=404)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=400)
        purchase = Purchase.objects.with_purchase_data().get(pk=purchase.pk)
        return Response(self.get_serializer(purchase).data)


class PurchaseCancelView(generics.GenericAPIView):
    permission_classes = (PurchaseAccessPermission,)
    permission_codename = "purchases.cancel_purchase"
    throttle_classes = (SensitiveActionThrottle,)
    serializer_class = PurchaseSerializer

    def post(self, request, pk):
        try:
            purchase = CancelPurchaseService.execute(purchase_id=pk)
        except Purchase.DoesNotExist:
            return Response({"detail": "Purchase not found."}, status=404)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=400)
        purchase = Purchase.objects.with_purchase_data().get(pk=purchase.pk)
        return Response(self.get_serializer(purchase).data)


class PurchaseDeleteView(generics.DestroyAPIView):
    serializer_class = PurchaseSerializer
    permission_classes = (PurchaseAccessPermission,)

    def get_queryset(self):
        return Purchase.objects.visible_to(self.request.user)

    def destroy(self, request, *args, **kwargs):
        try:
            DeletePurchase()(purchase_id=kwargs["pk"])
        except Purchase.DoesNotExist:
            return Response({"detail": "Purchase not found."}, status=404)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=409)
        return Response(status=204)


class PurchaseReturnView(generics.GenericAPIView):
    permission_classes = (PurchaseAccessPermission,)
    permission_codename = "purchases.return_purchase"
    throttle_classes = (SensitiveActionThrottle,)
    serializer_class = PurchaseReturnInputSerializer

    def post(self, request, pk):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        try:
            result = ReturnPurchase()(
                purchase_id=pk,
                items=data["items"],
                created_by_id=request.user.pk,
                reason=data.get("reason", ""),
            )
        except (ValueError, Purchase.DoesNotExist) as exc:
            return Response({"detail": str(exc)}, status=409)
        return Response(PurchaseReturnSerializer(result).data, status=status.HTTP_201_CREATED)
