"""Async ASGI views for immutable invoice operations."""

from asgiref.sync import sync_to_async
from django.db.models import Prefetch
from adrf import viewsets
from rest_framework import status
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


async def _invoice_response(operation):
    """Run an async use case and translate its domain errors to HTTP."""
    try:
        invoice = await operation()
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

    serializer = InvoiceSerializer(invoice)
    data = await sync_to_async(
        lambda: serializer.data,
        thread_sensitive=True,
    )()
    return Response(data, status=status.HTTP_200_OK)


class InvoiceViewSet(viewsets.ModelViewSet):
    """List, retrieve, and create invoices plus explicit lifecycle actions."""

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
        if self.action in {"list", "retrieve", "alist", "aretrieve"}:
            return InvoiceSummarySerializer
        return InvoiceSerializer

    async def acreate(self, request, *args, **kwargs):
        """Validate synchronously, then create through one transaction boundary."""
        serializer = self.get_serializer(data=request.data)
        await sync_to_async(
            serializer.is_valid,
            thread_sensitive=True,
        )(raise_exception=True)

        invoice = await CreateInvoice()(
            created_by_id=request.user.pk,
            validated_data=serializer.validated_data,
        )
        response_serializer = InvoiceSerializer(invoice)
        data = await sync_to_async(
            lambda: response_serializer.data,
            thread_sensitive=True,
        )()
        return Response(data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"], throttle_classes=[SensitiveActionThrottle])
    async def confirm(self, request, pk=None):
        return await _invoice_response(
            lambda: ConfirmInvoice()(invoice_id=pk)
        )

    @action(detail=True, methods=["post"], throttle_classes=[SensitiveActionThrottle])
    async def cancel(self, request, pk=None):
        return await _invoice_response(
            lambda: CancelInvoice()(invoice_id=pk)
        )

    @action(detail=True, methods=["post"], url_path="apply-coupon", throttle_classes=[SensitiveActionThrottle])
    async def apply_coupon(self, request, pk=None):
        code = (request.data or {}).get("code")
        if not code:
            return Response(
                {"detail": "A coupon code is required.", "code": "coupon_required"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return await _invoice_response(
            lambda: ApplyCoupon()(invoice_id=pk, code=code)
        )
