from django.db.models import Prefetch
from rest_framework import generics, status
from rest_framework.response import Response

from authentication.throttling import SensitiveActionThrottle
from common.exceptions import InvalidBusinessOperation, InvalidMoney
from common.pagination import StandardPagination
from common.observability import log_operation
from payments.api.serializers import (
    CollectionSerializer,
    PaymentTransactionSerializer,
    RefundInputSerializer,
)
from payments.models import PaymentAllocation, PaymentTransaction
from payments.permissions import CollectionPermission, RefundPermission, TransactionReadPermission
from payments.services import (
    NoConfirmableInvoicesError,
    OverpaymentError,
    process_idempotent,
    refund_payment,
)


class CollectionView(generics.GenericAPIView):
    serializer_class = CollectionSerializer
    permission_classes = (CollectionPermission,)
    throttle_classes = (SensitiveActionThrottle,)

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        key = request.headers.get("Idempotency-Key")
        if not key:
            return Response(
                {"detail": "Idempotency-Key header is required for payment collections.", "code": "idempotency_key_required"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        customer = serializer.validated_data["customer"]
        data = {
            "customer": customer.pk,
            "cash_amount": str(serializer.validated_data["cash_amount"]),
            "transfer_amount": str(serializer.validated_data["transfer_amount"]),
        }
        try:
            result = process_idempotent(
                key=key,
                user_id=request.user.pk,
                path=request.path,
                data=data,
                customer=customer,
                cash_amount=serializer.validated_data["cash_amount"],
                transfer_amount=serializer.validated_data["transfer_amount"],
            )
        except OverpaymentError as exc:
            return Response({"detail": str(exc), "code": "overpayment"}, status=400)
        except NoConfirmableInvoicesError as exc:
            return Response({"detail": str(exc), "code": "nothing_to_collect"}, status=400)
        except (InvalidMoney, InvalidBusinessOperation) as exc:
            return Response({"detail": str(exc), "code": "invalid_payment"}, status=400)
        if result == "mismatch":
            return Response({"detail": "Idempotency key used with a different request body.", "code": "idempotency_conflict"}, status=409)
        return Response(result.response_body, status=result.response_status)


class RefundView(generics.GenericAPIView):
    serializer_class = RefundInputSerializer
    permission_classes = (RefundPermission,)
    throttle_classes = (SensitiveActionThrottle,)

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        try:
            invoice = refund_payment(
                transaction_id=data["transaction"],
                invoice_id=data["invoice"],
                amount=data["amount"],
                created_by_id=request.user.pk,
                reason=data.get("reason", ""),
            )
        except (InvalidBusinessOperation, InvalidMoney) as exc:
            return Response({"detail": str(exc), "code": "refund_invalid"}, status=400)
        log_operation("payment.refund", user=request.user.pk, invoice=invoice.pk)
        return Response({"invoice": invoice.pk, "paid_amount": invoice.paid_amount, "outstanding_amount": invoice.outstanding_amount}, status=200)


class TransactionListView(generics.ListAPIView):
    serializer_class = PaymentTransactionSerializer
    pagination_class = StandardPagination
    permission_classes = (TransactionReadPermission,)

    def get_queryset(self):
        return (
            PaymentTransaction.objects.select_related("customer")
            .prefetch_related(
                Prefetch("allocations", queryset=PaymentAllocation.objects.select_related("invoice").prefetch_related("refunds")),
                "refunds",
            )
            .order_by("-created_at")
        )
