from django.db.models import Prefetch
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from accounts.models import RoleProfile
from authentication.throttling import SensitiveActionThrottle
from common.exceptions import (
    CouponInvalid,
    InsufficientStock,
    InvalidBusinessOperation,
    InvalidDiscount,
    InvalidStateTransition,
)
from common.idempotency import IdempotentResult, execute_idempotent
from common.services.approval_requests import request_approval
from invoices.api.filters import InvoiceFilter
from invoices.api.representative_sale import RepresentativeSaleSerializer
from invoices.api.serializers import (
    InvoiceReturnInputSerializer,
    InvoiceReturnSerializer,
    InvoiceSerializer,
    InvoiceSummarySerializer,
)
from invoices.models import Invoice, InvoiceItem
from invoices.permissions import InvoicePermission
from invoices.services import (
    ApplyCoupon,
    CancelInvoice,
    ConfirmInvoice,
    CreateInvoice,
    CreateSalesReturn,
    DeleteInvoice,
    InvoiceNotFound,
    RemoveCoupon,
    UpdateInvoice,
    create_representative_sale,
)


def _run_invoice(operation):
    try:
        return operation(), None
    except InvalidStateTransition as exc:
        return None, Response({"detail": str(exc), "code": "invalid_state_transition"}, status=409)
    except (CouponInvalid, InvalidDiscount) as exc:
        return None, Response({"detail": str(exc), "code": "coupon_invalid"}, status=400)
    except InsufficientStock as exc:
        return None, Response({"detail": str(exc), "code": "insufficient_stock"}, status=409)
    except (InvoiceNotFound, Invoice.DoesNotExist) as exc:
        return None, Response({"detail": str(exc) or "Invoice not found.", "code": "not_found"}, status=404)
    except InvalidBusinessOperation as exc:
        return None, Response({"detail": str(exc), "code": "invalid_operation"}, status=409)


def _idempotency_key(request):
    key = request.headers.get("Idempotency-Key", "").strip()
    return key if 1 <= len(key) <= 128 else None


class InvoiceViewSet(viewsets.ModelViewSet):
    permission_classes = (InvoicePermission,)
    filter_backends = (DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter)
    filterset_class = InvoiceFilter
    search_fields = ("customer__name",)
    ordering_fields = ("created_at", "updated_at", "status")
    ordering = ("-created_at", "-id")
    http_method_names = ("get", "post", "put", "patch", "delete", "head", "options")

    def get_queryset(self):
        return (
            Invoice.objects.visible_to(self.request.user)
            .select_related("customer", "created_by", "coupon")
            .prefetch_related(Prefetch("items", queryset=InvoiceItem.objects.select_related("product")))
        )

    def get_serializer_class(self):
        return InvoiceSummarySerializer if self.action == "list" else InvoiceSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        invoice, error = _run_invoice(
            lambda: CreateInvoice()(created_by=request.user, validated_data=serializer.validated_data)
        )
        if error:
            return error
        return Response(InvoiceSerializer(invoice, context={"request": request}).data, status=status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data, partial=request.method == "PATCH")
        serializer.is_valid(raise_exception=True)

        if RoleProfile.requires_shift_for_user(request.user):
            invoice = self.get_queryset().filter(pk=kwargs["pk"], created_by_id=request.user.pk).first()
            if invoice is None:
                return Response({"detail": "Invoice not found.", "code": "not_found"}, status=404)
            data = serializer.validated_data
            requested_items = data.get("items")
            if requested_items is None:
                requested_items = [
                    {"product": item.product_id, "quantity": item.quantity}
                    for item in invoice.items.all()
                ]
            payload = {
                "customer": data.get("customer", invoice.customer_id).pk
                if hasattr(data.get("customer", invoice.customer_id), "pk")
                else data.get("customer", invoice.customer_id),
                "items": [
                    {"product": item["product"].pk if hasattr(item["product"], "pk") else item["product"], "quantity": item["quantity"]}
                    for item in requested_items
                ],
            }
            key = _idempotency_key(request)
            if not key:
                return Response({"detail": "A valid Idempotency-Key header is required.", "code": "idempotency_key_required"}, status=400)
            try:
                result = request_approval(
                    requester=request.user,
                    target_type="invoice",
                    target_id=invoice.pk,
                    operation="update",
                    payload=payload,
                    reason="Invoice edit requested from representative app",
                    idempotency_key=key,
                    path=request.path,
                )
            except InvalidBusinessOperation as exc:
                return Response({"detail": str(exc), "code": "approval_invalid"}, status=409)
            if result == "mismatch":
                return Response({"detail": "Idempotency key used with a different request body.", "code": "idempotency_conflict"}, status=409)
            return Response(result.response_body, status=result.response_status)

        invoice, error = _run_invoice(
            lambda: UpdateInvoice()(invoice_id=kwargs["pk"], validated_data=serializer.validated_data, actor=request.user)
        )
        if error:
            return error
        return Response(InvoiceSerializer(invoice, context={"request": request}).data)

    def partial_update(self, request, *args, **kwargs):
        return self.update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        if RoleProfile.requires_shift_for_user(request.user):
            invoice = self.get_queryset().filter(pk=kwargs["pk"], created_by_id=request.user.pk).first()
            if invoice is None:
                return Response({"detail": "Invoice not found.", "code": "not_found"}, status=404)
            key = _idempotency_key(request)
            if not key:
                return Response({"detail": "A valid Idempotency-Key header is required.", "code": "idempotency_key_required"}, status=400)
            try:
                result = request_approval(
                    requester=request.user,
                    target_type="invoice",
                    target_id=invoice.pk,
                    operation="delete",
                    payload={},
                    reason="Invoice deletion requested from representative app",
                    idempotency_key=key,
                    path=request.path,
                )
            except InvalidBusinessOperation as exc:
                return Response({"detail": str(exc), "code": "approval_invalid"}, status=409)
            if result == "mismatch":
                return Response({"detail": "Idempotency key used with a different request body.", "code": "idempotency_conflict"}, status=409)
            return Response(result.response_body, status=result.response_status)

        _, error = _run_invoice(lambda: DeleteInvoice()(invoice_id=kwargs["pk"], actor=request.user))
        if error:
            return error
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=False, methods=["post"], url_path="representative-sale", throttle_classes=[SensitiveActionThrottle])
    def representative_sale(self, request):
        serializer = RepresentativeSaleSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        key = _idempotency_key(request)
        if not key:
            return Response({"detail": "A valid Idempotency-Key header is required.", "code": "idempotency_key_required"}, status=400)
        if not request.user.has_perm("invoices.confirm_invoice"):
            return Response({"detail": "Representative sale confirmation is not permitted.", "code": "permission_denied"}, status=403)
        if serializer.validated_data["payment_amount"] > 0 and not request.user.has_perm("payments.process_collection"):
            return Response({"detail": "Payment collection is not permitted for this user.", "code": "permission_denied"}, status=403)

        data = serializer.validated_data
        signature_body = {
            "customer": data["customer"].pk,
            "items": [{"product": item["product"].pk, "quantity": item["quantity"]} for item in data["items"]],
            "payment_method": data["payment_method"],
            "payment_amount": str(data["payment_amount"]),
        }

        def create_sale():
            invoice, _payment = create_representative_sale(
                customer=data["customer"],
                items=data["items"],
                payment_method=data["payment_method"],
                payment_amount=data["payment_amount"],
                representative=request.user,
            )
            return IdempotentResult(
                status=201,
                body={"invoice": InvoiceSerializer(invoice, context={"request": request}).data},
            )

        try:
            result = execute_idempotent(
                key=key,
                user_id=request.user.pk,
                path=request.path,
                data=signature_body,
                operation=create_sale,
            )
        except (InsufficientStock, InvalidBusinessOperation) as exc:
            return Response({"detail": str(exc), "code": "sale_invalid"}, status=409)
        if result == "mismatch":
            return Response({"detail": "Idempotency key used with a different request body.", "code": "idempotency_conflict"}, status=409)
        return Response(result.response_body, status=result.response_status)

    @action(detail=True, methods=["post"], throttle_classes=[SensitiveActionThrottle])
    def confirm(self, request, pk=None):
        invoice, error = _run_invoice(lambda: ConfirmInvoice()(invoice_id=pk, actor=request.user))
        if error:
            return error
        return Response(InvoiceSerializer(invoice, context={"request": request}).data)

    @action(detail=True, methods=["post"], throttle_classes=[SensitiveActionThrottle])
    def cancel(self, request, pk=None):
        invoice, error = _run_invoice(lambda: CancelInvoice()(invoice_id=pk, actor=request.user))
        if error:
            return error
        return Response(InvoiceSerializer(invoice, context={"request": request}).data)

    @action(detail=True, methods=["post"], url_path="apply-coupon", throttle_classes=[SensitiveActionThrottle])
    def apply_coupon(self, request, pk=None):
        code = (request.data or {}).get("code")
        if not code:
            return Response({"detail": "A coupon code is required.", "code": "coupon_required"}, status=400)
        invoice, error = _run_invoice(lambda: ApplyCoupon()(invoice_id=pk, code=code, actor=request.user))
        if error:
            return error
        return Response(InvoiceSerializer(invoice, context={"request": request}).data)

    @action(detail=True, methods=["post"], url_path="remove-coupon", throttle_classes=[SensitiveActionThrottle])
    def remove_coupon(self, request, pk=None):
        invoice, error = _run_invoice(lambda: RemoveCoupon()(invoice_id=pk, actor=request.user))
        if error:
            return error
        return Response(InvoiceSerializer(invoice, context={"request": request}).data)

    @action(detail=True, methods=["post"], throttle_classes=[SensitiveActionThrottle], url_path="returns")
    def returns(self, request, pk=None):
        serializer = InvoiceReturnInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        result, error = _run_invoice(
            lambda: CreateSalesReturn()(invoice_id=pk, items=data["items"], created_by_id=request.user.pk, reason=data.get("reason", ""), actor=request.user)
        )
        if error:
            return error
        return Response(InvoiceReturnSerializer(result, context={"request": request}).data, status=status.HTTP_201_CREATED)
