"""Synchronous API views for invoice operations."""

from django.db.models import Prefetch
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from authentication.throttling import SensitiveActionThrottle
from common.exceptions import (
    CouponInvalid,
    InsufficientStock,
    InvalidBusinessOperation,
    InvalidDiscount,
    InvalidStateTransition,
)
from invoices.api.serializers import InvoiceSerializer, InvoiceSummarySerializer
from invoices.models import Invoice, InvoiceItem
from invoices.permissions import InvoicePermission
from invoices.services import (
    ApplyCoupon,
    CancelInvoice,
    ConfirmInvoice,
    CreateInvoice,
    InvoiceNotFound,
)


def _invoice_response(operation):
    """Run an invoice use case and translate domain errors to HTTP."""
    try:
        invoice = operation()
    except InvalidStateTransition as exc:
        return Response(
            {"detail": str(exc), "code": "invalid_state_transition"},
            status=status.HTTP_409_CONFLICT,
        )
    except (CouponInvalid, InvalidDiscount) as exc:
        return Response(
            {"detail": str(exc), "code": "coupon_invalid"},
            status=status.HTTP_400_BAD_REQUEST,
        )
    except InsufficientStock as exc:
        return Response(
            {"detail": str(exc), "code": "insufficient_stock"},
            status=status.HTTP_409_CONFLICT,
        )
    except InvoiceNotFound as exc:
        return Response(
            {"detail": str(exc), "code": "not_found"},
            status=status.HTTP_404_NOT_FOUND,
        )
    except InvalidBusinessOperation as exc:
        return Response(
            {"detail": str(exc), "code": "invalid_operation"},
            status=status.HTTP_409_CONFLICT,
        )

    return Response(
        InvoiceSerializer(invoice).data,
        status=status.HTTP_200_OK,
    )


class InvoiceViewSet(viewsets.ModelViewSet):
    """List, retrieve, create, and execute explicit invoice lifecycle actions."""

    permission_classes = (InvoicePermission,)
    http_method_names = ("get", "post", "head", "options")

    def get_queryset(self):
        return Invoice.objects.select_related(
            "customer",
            "created_by",
            "coupon",
        ).prefetch_related(
            Prefetch(
                "items",
                queryset=InvoiceItem.objects.select_related("product"),
            )
        )

    def get_serializer_class(self):
        if self.action in {"list", "retrieve"}:
            return InvoiceSummarySerializer
        return InvoiceSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        invoice = CreateInvoice()(
            created_by_id=request.user.pk,
            validated_data=serializer.validated_data,
        )
        return Response(
            InvoiceSerializer(invoice).data,
            status=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=["post"], throttle_classes=[SensitiveActionThrottle])
    def confirm(self, request, pk=None):
        return _invoice_response(lambda: ConfirmInvoice()(invoice_id=pk))

    @action(detail=True, methods=["post"], throttle_classes=[SensitiveActionThrottle])
    def cancel(self, request, pk=None):
        return _invoice_response(lambda: CancelInvoice()(invoice_id=pk))

    @action(
        detail=True,
        methods=["post"],
        url_path="apply-coupon",
        throttle_classes=[SensitiveActionThrottle],
    )
    def apply_coupon(self, request, pk=None):
        code = (request.data or {}).get("code")
        if not code:
            return Response(
                {"detail": "A coupon code is required.", "code": "coupon_required"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return _invoice_response(lambda: ApplyCoupon()(invoice_id=pk, code=code))
