from rest_framework import serializers, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from common.exceptions import InvalidBusinessOperation
from common.services.approval_requests import (
    list_pending_for_manager,
    request_approval,
    review_approval,
)


class ApprovalRequestCreateSerializer(serializers.Serializer):
    target_type = serializers.ChoiceField(choices=("invoice", "vehicle"))
    target_id = serializers.IntegerField(min_value=1)
    operation = serializers.ChoiceField(choices=("update", "delete"))
    payload = serializers.JSONField(required=False, default=dict)
    reason = serializers.CharField(required=False, allow_blank=True, max_length=500)


class ApprovalReviewSerializer(serializers.Serializer):
    reason = serializers.CharField(required=False, allow_blank=True, max_length=500)


class ApprovalRequestListCreateView(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        return Response({"results": list_pending_for_manager(manager=request.user)})

    def post(self, request):
        serializer = ApprovalRequestCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        key = request.headers.get("Idempotency-Key", "").strip()
        if not key or len(key) > 128:
            return Response(
                {"detail": "A valid Idempotency-Key header is required.", "code": "idempotency_key_required"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            result = request_approval(
                requester=request.user,
                target_type=serializer.validated_data["target_type"],
                target_id=serializer.validated_data["target_id"],
                operation=serializer.validated_data["operation"],
                payload=serializer.validated_data.get("payload") or {},
                reason=serializer.validated_data.get("reason", ""),
                idempotency_key=key,
                path=request.path,
            )
        except InvalidBusinessOperation as exc:
            return Response({"detail": str(exc), "code": "approval_invalid"}, status=409)
        if result == "mismatch":
            return Response(
                {"detail": "Idempotency key used with a different request body.", "code": "idempotency_conflict"},
                status=409,
            )
        return Response(result.response_body, status=result.response_status)


class ApprovalReviewView(APIView):
    permission_classes = (IsAuthenticated,)

    def post(self, request, approval_event_id, decision):
        if decision not in {"approve", "reject"}:
            return Response({"detail": "Unsupported decision."}, status=400)
        serializer = ApprovalReviewSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        key = request.headers.get("Idempotency-Key", "").strip()
        if not key or len(key) > 128:
            return Response(
                {"detail": "A valid Idempotency-Key header is required.", "code": "idempotency_key_required"},
                status=400,
            )
        try:
            result = review_approval(
                approver=request.user,
                approval_event_id=approval_event_id,
                decision=decision,
                reason=serializer.validated_data.get("reason", ""),
                idempotency_key=key,
                path_prefix="/api/v1/approvals/",
            )
        except InvalidBusinessOperation as exc:
            return Response({"detail": str(exc), "code": "approval_invalid"}, status=409)
        if result == "mismatch":
            return Response(
                {"detail": "Idempotency key used with a different request body.", "code": "idempotency_conflict"},
                status=409,
            )
        return Response(result.response_body, status=result.response_status)
