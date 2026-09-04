from adrf import viewsets
from rest_framework import status
from rest_framework import filters
from rest_framework.response import Response

from common.exceptions import InvalidBusinessOperation
from common.permissions import ReadAuthenticatedWriteStaffPermission

from coupons.api.serializers import CouponSerializer
from coupons.models import Coupon
from coupons.services import DeleteCoupon


class CouponViewSet(viewsets.ModelViewSet):
    permission_classes = (
        ReadAuthenticatedWriteStaffPermission,
    )

    serializer_class = CouponSerializer

    filter_backends = (
        filters.SearchFilter,
        filters.OrderingFilter,
    )

    search_fields = (
        "code",
    )

    ordering_fields = (
        "code",
        "discount_type",
        "discount_value",
        "minimum_invoice_amount",
        "is_active",
        "valid_from",
        "valid_until",
        "created_at",
        "updated_at",
    )

    ordering = (
        "code",
        "pk",
    )

    def get_queryset(self):
        return Coupon.objects.all()

    async def adestroy(self, request, *args, **kwargs):
        instance = await self.aget_object()
        try:
            await DeleteCoupon()(instance=instance)
        except InvalidBusinessOperation as exc:
            return Response(
                {"detail": str(exc), "code": "coupon_in_use"},
                status=status.HTTP_409_CONFLICT,
            )
        return Response(status=status.HTTP_204_NO_CONTENT)
