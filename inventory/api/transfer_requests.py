from django.db.models import Q
from rest_framework import generics, serializers, status
from rest_framework.response import Response

from common.idempotency import IdempotentResult, execute_idempotent
from inventory.models import StockTransferRequest, StockTransferRequestItem
from inventory.permissions import InventoryTransferRequestPermission, InventoryReadPermission
from inventory.services.approval import can_approve_stock_request
from inventory.services.transfer_requests import (
    StockTransferRequestError,
    approve_stock_transfer_request,
    create_stock_transfer_request,
    reject_stock_transfer_request,
)
from products.models import Product
from invoices.models import Invoice, InvoiceItem


class WarehouseManagerOptionSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    name = serializers.CharField()
    username = serializers.CharField()


class StockTransferRequestItemOutputSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source="product.name", read_only=True)
    invoice_item_id = serializers.IntegerField(source="invoice_item.id", read_only=True, allow_null=True)

    class Meta:
        model = StockTransferRequestItem
        fields = ("id", "product", "product_name", "quantity", "invoice_item_id")
        read_only_fields = fields


class StockTransferRequestOutputSerializer(serializers.ModelSerializer):
    requested_by_name = serializers.SerializerMethodField()
    warehouse_manager_name = serializers.SerializerMethodField()
    approved_by_name = serializers.SerializerMethodField()
    warehouse_name = serializers.CharField(source="warehouse.name", read_only=True)
    source_location_name = serializers.CharField(source="source_location.name", read_only=True)
    destination_location_name = serializers.CharField(source="destination_location.name", read_only=True)
    items = StockTransferRequestItemOutputSerializer(many=True, read_only=True)

    class Meta:
        model = StockTransferRequest
        fields = (
            "id", "request_type", "requested_by", "requested_by_name",
            "warehouse_manager", "warehouse_manager_name", "approved_by", "approved_by_name",
            "shift", "warehouse", "warehouse_name", "source_location", "source_location_name",
            "destination_location", "destination_location_name", "status", "reference",
            "rejection_reason", "created_at", "reviewed_at", "approved_movement", "invoice_return", "items",
        )
        read_only_fields = fields

    def get_requested_by_name(self, obj):
        return obj.requested_by.get_full_name() or obj.requested_by.username

    def get_warehouse_manager_name(self, obj):
        return obj.warehouse_manager.get_full_name() or obj.warehouse_manager.username

    def get_approved_by_name(self, obj):
        if obj.approved_by_id is None:
            return None
        return obj.approved_by.get_full_name() or obj.approved_by.username


class StockTransferRequestItemInputSerializer(serializers.Serializer):
    product = serializers.PrimaryKeyRelatedField(queryset=Product.objects.active())
    quantity = serializers.IntegerField(min_value=1)
    invoice_item = serializers.PrimaryKeyRelatedField(
        queryset=InvoiceItem.objects.select_related("invoice", "product"),
        required=False,
        allow_null=True,
    )


class StockTransferRequestCreateSerializer(serializers.Serializer):
    request_type = serializers.ChoiceField(choices=StockTransferRequest.RequestType.choices)
    warehouse = serializers.IntegerField(min_value=1)
    warehouse_manager = serializers.IntegerField(min_value=1)
    invoice = serializers.IntegerField(min_value=1, required=False, allow_null=True)
    reference = serializers.CharField(required=False, allow_blank=True, max_length=100)
    items = StockTransferRequestItemInputSerializer(many=True)

    def validate_items(self, value):
        if not value:
            raise serializers.ValidationError("A stock request must contain at least one item.")
        product_ids = [item["product"].pk for item in value]
        if len(product_ids) != len(set(product_ids)):
            raise serializers.ValidationError("A product can appear only once in a stock request.")
        return value

    def validate(self, attrs):
        request_type = attrs["request_type"]
        invoice_id = attrs.get("invoice")
        items = attrs["items"]
        if request_type == StockTransferRequest.RequestType.VEHICLE_TO_WAREHOUSE:
            if invoice_id is None:
                raise serializers.ValidationError({"invoice": "An invoice is required for a customer return request."})
            invoice = Invoice.objects.filter(pk=invoice_id).first()
            if invoice is None:
                raise serializers.ValidationError({"invoice": "The selected invoice does not exist."})
            invoice_item_ids = [item["invoice_item"].pk if item.get("invoice_item") else None for item in items]
            if any(item_id is None for item_id in invoice_item_ids):
                raise serializers.ValidationError({"items": "Every return item must reference an invoice item."})
            for item in items:
                invoice_item = item["invoice_item"]
                if invoice_item.invoice_id != invoice_id:
                    raise serializers.ValidationError({"items": "All return items must belong to the selected invoice."})
                if invoice_item.product_id != item["product"].pk:
                    raise serializers.ValidationError({"items": "The product must match the selected invoice item."})
        elif invoice_id is not None:
            raise serializers.ValidationError({"invoice": "An invoice is allowed only for vehicle return requests."})
        return attrs


class WarehouseManagerOptionsView(generics.ListAPIView):
    permission_classes = (InventoryReadPermission,)
    permission_codename = "inventory.view_stocklocation"
    serializer_class = WarehouseManagerOptionSerializer

    def get_queryset(self):
        warehouse_id = self.request.query_params.get("warehouse")
        if not warehouse_id:
            return []
        from inventory.models import StockLocation

        warehouse = (
            StockLocation.objects
            .filter(pk=warehouse_id, location_type=StockLocation.LocationType.MAIN_WAREHOUSE, is_active=True)
            .prefetch_related("warehouse_managers")
            .first()
        )
        if warehouse is None:
            return []

        managers = [
            user
            for user in warehouse.warehouse_managers.all()
            if user.is_active
            and can_approve_stock_request(approver=user, requester=self.request.user)
        ]
        return managers

    def list(self, request, *args, **kwargs):
        managers = self.get_queryset()
        data = [
            {
                "id": user.pk,
                "name": user.get_full_name() or user.username,
                "username": user.username,
            }
            for user in managers
        ]
        return Response(data)


class StockTransferRequestListCreateView(generics.ListCreateAPIView):
    serializer_class = StockTransferRequestOutputSerializer
    permission_classes = (InventoryTransferRequestPermission,)

    def get_queryset(self):
        user = self.request.user
        queryset = (
            StockTransferRequest.objects
            .select_related(
                "requested_by", "warehouse_manager", "approved_by", "shift",
                "warehouse", "source_location", "destination_location",
            )
            .prefetch_related("items__product", "items__invoice_item")
        )
        if user.is_superuser:
            return queryset
        return queryset.filter(Q(requested_by=user) | Q(warehouse_manager=user)).distinct()

    def create(self, request, *args, **kwargs):
        serializer = StockTransferRequestCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        key = request.headers.get("Idempotency-Key", "").strip()
        if not key or len(key) > 128:
            return Response(
                {"detail": "A valid Idempotency-Key header is required.", "code": "idempotency_key_required"},
                status=400,
            )
        signature_body = {
            "request_type": data["request_type"],
            "warehouse": data["warehouse"],
            "warehouse_manager": data["warehouse_manager"],
            "invoice": data.get("invoice"),
            "reference": data.get("reference", ""),
            "items": [
                {
                    "product": item["product"].pk,
                    "quantity": item["quantity"],
                    "invoice_item": item.get("invoice_item").pk if item.get("invoice_item") else None,
                }
                for item in data["items"]
            ],
        }

        def create_request():
            try:
                transfer_request = create_stock_transfer_request(
                    requested_by=request.user,
                    request_type=data["request_type"],
                    warehouse_id=data["warehouse"],
                    warehouse_manager_id=data["warehouse_manager"],
                    items=data["items"],
                    invoice_id=data.get("invoice"),
                    reference=data.get("reference", ""),
                )
            except StockTransferRequestError as exc:
                raise exc

            transfer_request = self.get_queryset().get(pk=transfer_request.pk)
            return IdempotentResult(
                status=status.HTTP_201_CREATED,
                body=StockTransferRequestOutputSerializer(
                    transfer_request,
                    context={"request": request},
                ).data,
            )

        try:
            result = execute_idempotent(
                key=key,
                user_id=request.user.pk,
                path=request.path,
                data=signature_body,
                operation=create_request,
            )
        except StockTransferRequestError as exc:
            return Response({"detail": str(exc), "code": "stock_request_invalid"}, status=status.HTTP_409_CONFLICT)
        if result == "mismatch":
            return Response(
                {"detail": "Idempotency key used with a different request body.", "code": "idempotency_conflict"},
                status=status.HTTP_409_CONFLICT,
            )
        return Response(result.response_body, status=result.response_status)


class StockTransferRequestApproveView(generics.GenericAPIView):
    permission_classes = (InventoryReadPermission,)
    permission_codename = "inventory.approve_stock_transfer"

    def post(self, request, pk, *args, **kwargs):
        key = request.headers.get("Idempotency-Key", "").strip()
        if not key or len(key) > 128:
            return Response({"detail": "A valid Idempotency-Key header is required.", "code": "idempotency_key_required"}, status=400)

        def approve():
            try:
                transfer_request = approve_stock_transfer_request(
                    request_id=pk,
                    approver=request.user,
                )
            except StockTransferRequest.DoesNotExist:
                return IdempotentResult(status=404, body={"detail": "Stock transfer request not found."})
            except StockTransferRequestError as exc:
                return IdempotentResult(status=409, body={"detail": str(exc), "code": "stock_request_approval_invalid"})

            transfer_request = (
                StockTransferRequest.objects
                .select_related("requested_by", "warehouse_manager", "approved_by", "shift", "warehouse", "source_location", "destination_location")
                .prefetch_related("items__product", "items__invoice_item")
                .get(pk=transfer_request.pk)
            )
            return IdempotentResult(
                status=200,
                body=StockTransferRequestOutputSerializer(transfer_request, context={"request": request}).data,
            )

        result = execute_idempotent(
            key=key,
            user_id=request.user.pk,
            path=request.path,
            data={"request_id": pk, "decision": "approve"},
            operation=approve,
        )
        if result == "mismatch":
            return Response({"detail": "Idempotency key used with a different request body.", "code": "idempotency_conflict"}, status=409)
        return Response(result.response_body, status=result.response_status)


class StockTransferRequestRejectView(generics.GenericAPIView):
    permission_classes = (InventoryReadPermission,)
    permission_codename = "inventory.approve_stock_transfer"

    def post(self, request, pk, *args, **kwargs):
        key = request.headers.get("Idempotency-Key", "").strip()
        if not key or len(key) > 128:
            return Response({"detail": "A valid Idempotency-Key header is required.", "code": "idempotency_key_required"}, status=400)
        reason = str((request.data or {}).get("reason", ""))

        def reject():
            try:
                transfer_request = reject_stock_transfer_request(
                    request_id=pk,
                    approver=request.user,
                    reason=reason,
                )
            except StockTransferRequest.DoesNotExist:
                return IdempotentResult(status=404, body={"detail": "Stock transfer request not found."})
            except StockTransferRequestError as exc:
                return IdempotentResult(status=409, body={"detail": str(exc), "code": "stock_request_rejection_invalid"})

            transfer_request = (
                StockTransferRequest.objects
                .select_related("requested_by", "warehouse_manager", "approved_by", "shift", "warehouse", "source_location", "destination_location")
                .prefetch_related("items__product", "items__invoice_item")
                .get(pk=transfer_request.pk)
            )
            return IdempotentResult(
                status=200,
                body=StockTransferRequestOutputSerializer(transfer_request, context={"request": request}).data,
            )

        result = execute_idempotent(
            key=key,
            user_id=request.user.pk,
            path=request.path,
            data={"request_id": pk, "decision": "reject", "reason": reason},
            operation=reject,
        )
        if result == "mismatch":
            return Response({"detail": "Idempotency key used with a different request body.", "code": "idempotency_conflict"}, status=409)
        return Response(result.response_body, status=result.response_status)
