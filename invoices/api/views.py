from django.db.models import Prefetch
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from authentication.throttling import SensitiveActionThrottle
from common.exceptions import CouponInvalid, InsufficientStock, InvalidBusinessOperation, InvalidDiscount, InvalidStateTransition
from invoices.api.serializers import InvoiceReturnInputSerializer, InvoiceReturnSerializer, InvoiceSerializer, InvoiceSummarySerializer
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
    except InvoiceNotFound as exc:
        return None, Response({"detail": str(exc), "code": "not_found"}, status=404)
    except InvalidBusinessOperation as exc:
        return None, Response({"detail": str(exc), "code": "invalid_operation"}, status=409)


class InvoiceViewSet(viewsets.ModelViewSet):
    permission_classes = (InvoicePermission,)
    http_method_names = ("get", "post", "put", "patch", "delete", "head", "options")

    def get_queryset(self):
        return (
            Invoice.objects.visible_to(self.request.user)
            .select_related("customer", "created_by", "coupon")
            .prefetch_related(Prefetch("items", queryset=InvoiceItem.objects.select_related("product")))
        )

    def get_serializer_class(self):
        if self.action in {"list", "retrieve"}:
            return InvoiceSummarySerializer
        return InvoiceSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        invoice = CreateInvoice()(created_by_id=request.user.pk, validated_data=serializer.validated_data)
        return Response(InvoiceSerializer(invoice).data, status=status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        invoice, error = _run_invoice(
            lambda: UpdateInvoice()(invoice_id=kwargs["pk"], validated_data=request.data)
        )
        if error:
            return error
        return Response(InvoiceSerializer(invoice).data)

    def partial_update(self, request, *args, **kwargs):
        return self.update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        _, error = _run_invoice(lambda: DeleteInvoice()(invoice_id=kwargs["pk"]))
        if error:
            return error
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=["post"], throttle_classes=[SensitiveActionThrottle])
    def confirm(self, request, pk=None):
        invoice, error = _run_invoice(lambda: ConfirmInvoice()(invoice_id=pk))
        if error:
            return error
        return Response(InvoiceSerializer(invoice).data)

    @action(detail=True, methods=["post"], throttle_classes=[SensitiveActionThrottle])
    def cancel(self, request, pk=None):
        invoice, error = _run_invoice(lambda: CancelInvoice()(invoice_id=pk))
        if error:
            return error
        return Response(InvoiceSerializer(invoice).data)

    @action(detail=True, methods=["post"], url_path="apply-coupon", throttle_classes=[SensitiveActionThrottle])
    def apply_coupon(self, request, pk=None):
        code = (request.data or {}).get("code")
        if not code:
            return Response({"detail": "A coupon code is required.", "code": "coupon_required"}, status=400)
        invoice, error = _run_invoice(lambda: ApplyCoupon()(invoice_id=pk, code=code))
        if error:
            return error
        return Response(InvoiceSerializer(invoice).data)

    @action(detail=True, methods=["post"], url_path="remove-coupon", throttle_classes=[SensitiveActionThrottle])
    def remove_coupon(self, request, pk=None):
        invoice, error = _run_invoice(lambda: RemoveCoupon()(invoice_id=pk))
        if error:
            return error
        return Response(InvoiceSerializer(invoice).data)

    @action(detail=True, methods=["post"], throttle_classes=[SensitiveActionThrottle], url_path="returns")
    def returns(self, request, pk=None):
        serializer = InvoiceReturnInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        result, error = _run_invoice(
            lambda: CreateSalesReturn()(
                invoice_id=pk,
                items=data["items"],
                created_by_id=request.user.pk,
                reason=data.get("reason", ""),
            )
        )
        if error:
            return error
        return Response(InvoiceReturnSerializer(result).data, status=201)
