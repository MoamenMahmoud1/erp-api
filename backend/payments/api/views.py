from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, generics, status
from rest_framework.response import Response

from authentication.throttling import SensitiveActionThrottle
from common.exceptions import InvalidBusinessOperation, InvalidMoney
from common.pagination import StandardPagination
from common.observability import log_operation
from payments.api.filters import PaymentTransactionFilter
from invoices.models import Invoice
from payments.api.serializers import CollectionSerializer, PaymentTransactionSerializer, RefundInputSerializer
from payments.models import PaymentTransaction
from payments.permissions import CollectionPermission, RefundPermission, TransactionReadPermission, TransferApprovalPermission
from payments.services import (
    NoConfirmableInvoicesError,
    OverpaymentError,
    approve_bank_transfer,
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
            return Response({"detail": "Idempotency-Key header is required for payment collections.", "code": "idempotency_key_required"}, status=400)
        data = serializer.validated_data
        customer = data["customer"]
        invoice_id = data.get("invoice")
        if invoice_id is not None:
            invoice = Invoice.objects.filter(pk=invoice_id, customer=customer).first()
            if invoice is None:
                return Response({"detail": "The selected invoice does not belong to this customer.", "code": "invoice_customer_mismatch"}, status=400)

        try:
            result = process_idempotent(
                key=key,
                user_id=request.user.pk,
                path=request.path,
                data={
                    "customer": customer.pk,
                    "invoice": invoice_id,
                    "cash_amount": str(data["cash_amount"]),
                    "transfer_amount": str(data["transfer_amount"]),
                },
                customer=customer,
                invoice_id=invoice_id,
                cash_amount=data["cash_amount"],
                transfer_amount=data["transfer_amount"],
                actor=request.user,
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
                actor=request.user,
            )
        except (InvalidBusinessOperation, InvalidMoney) as exc:
            return Response({"detail": str(exc), "code": "refund_invalid"}, status=400)
        log_operation("payment.refund", user=request.user.pk, invoice=invoice.pk)
        return Response({"invoice": invoice.pk, "paid_amount": invoice.paid_amount, "outstanding_amount": invoice.outstanding_amount})


class TransferApprovalView(generics.GenericAPIView):
    permission_classes = (TransferApprovalPermission,)
    throttle_classes = (SensitiveActionThrottle,)

    def post(self, request, pk, *args, **kwargs):
        try:
            payment = approve_bank_transfer(
                transaction_id=pk,
                actor_id=request.user.pk,
                actor=request.user,
            )
        except (InvalidBusinessOperation, InvalidMoney) as exc:
            return Response(
                {"detail": str(exc), "code": "transfer_approval_invalid"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(
            PaymentTransactionSerializer(payment).data,
            status=status.HTTP_200_OK,
        )


class TransactionListView(generics.ListAPIView):
    serializer_class = PaymentTransactionSerializer
    pagination_class = StandardPagination
    permission_classes = (TransactionReadPermission,)
    filter_backends = (DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter)
    filterset_class = PaymentTransactionFilter
    search_fields = (
        "customer__name",
        "collected_by__username",
        "collected_by__email",
        "collected_by__first_name",
        "collected_by__last_name",
    )
    ordering_fields = ("created_at", "cash_amount", "transfer_amount")
    ordering = ("-created_at", "-id")

    def get_queryset(self):
        return PaymentTransaction.objects.visible_to(self.request.user).with_payment_data().order_by("-created_at")


class TransactionDetailView(generics.RetrieveAPIView):
    serializer_class = PaymentTransactionSerializer
    permission_classes = (TransactionReadPermission,)

    def get_queryset(self):
        return PaymentTransaction.objects.visible_to(self.request.user).with_payment_data()
