"""Async payment/collection API."""

from asgiref.sync import sync_to_async
from adrf import generics
from adrf.views import APIView
from django.db.models import Prefetch
from rest_framework import status
from rest_framework.response import Response

from common.exceptions import InvalidBusinessOperation, InvalidMoney
from common.pagination import StandardPagination
from common.observability import log_operation
from payments.api.serializers import (
    CollectionSerializer,
    PaymentTransactionSerializer,
)
from payments.models import PaymentAllocation, PaymentTransaction
from payments.permissions import CollectionPermission, TransactionReadPermission
from payments.services import (
    NoConfirmableInvoicesError,
    OverpaymentError,
    ProcessCollectionIdempotent,
)
from authentication.throttling import SensitiveActionThrottle


class CollectionView(APIView):
    """POST /api/v1/payments/collections/ — receive and allocate a payment."""

    permission_classes = (CollectionPermission,)
    throttle_classes = (SensitiveActionThrottle,)

    async def post(self, request, *args, **kwargs):
        serializer = CollectionSerializer(data=request.data)
        await sync_to_async(
            serializer.is_valid,
            thread_sensitive=True,
        )(raise_exception=True)

        idempotency_key = request.headers.get("Idempotency-Key")
        if not idempotency_key:
            return Response(
                {
                    "detail": "Idempotency-Key header is required for payment collections.",
                    "code": "idempotency_key_required",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        customer = serializer.validated_data["customer"]
        cash_amount = serializer.validated_data["cash_amount"]
        transfer_amount = serializer.validated_data["transfer_amount"]

        request_data = {
            "customer": customer.pk,
            "cash_amount": str(cash_amount),
            "transfer_amount": str(transfer_amount),
        }
        user_id = request.user.pk

        try:
            result = await ProcessCollectionIdempotent()(
                key=idempotency_key,
                user_id=user_id,
                path=request.path,
                data=request_data,
                customer=customer,
                cash_amount=cash_amount,
                transfer_amount=transfer_amount,
            )
        except OverpaymentError as exc:
            log_operation("payment.collection", user=user_id,
                          customer=customer.pk, result="overpayment_rejected")
            return Response(
                {"detail": str(exc), "code": "overpayment"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except NoConfirmableInvoicesError as exc:
            log_operation("payment.collection", user=user_id,
                          customer=customer.pk, result="no_invoices_rejected")
            return Response(
                {"detail": str(exc), "code": "nothing_to_collect"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except (InvalidMoney, InvalidBusinessOperation) as exc:
            log_operation("payment.collection", user=user_id,
                          customer=customer.pk, result="invalid_rejected")
            return Response(
                {"detail": str(exc), "code": "invalid_payment"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if result == "mismatch":
            return Response(
                {
                    "detail": "Idempotency key used with a different request body.",
                    "code": "idempotency_conflict",
                },
                status=status.HTTP_409_CONFLICT,
            )

        return Response(
            result.response_body,
            status=result.response_status,
        )


class TransactionListView(generics.ListAPIView):
    """GET /api/v1/payments/transactions/ — read-only view of collections."""

    serializer_class = PaymentTransactionSerializer
    pagination_class = StandardPagination
    permission_classes = (TransactionReadPermission,)

    def get_queryset(self):
        return (
            PaymentTransaction.objects.select_related("customer")
            .prefetch_related(
                Prefetch(
                    "allocations",
                    queryset=PaymentAllocation.objects.select_related("invoice"),
                )
            )
            .order_by("-created_at")
        )
