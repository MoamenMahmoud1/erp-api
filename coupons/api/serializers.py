from django.core.exceptions import ValidationError as DjangoValidationError
from adrf import serializers
from rest_framework.exceptions import ValidationError

from coupons.models import Coupon
from coupons.services import CreateCoupon, UpdateCoupon
from coupons.services.create import create_coupon_sync
from coupons.services.update import update_coupon_sync


class CouponSerializer(serializers.ModelSerializer):
    class Meta:
        model = Coupon
        fields = "__all__"

        read_only_fields = (
            "id",
            "created_at",
            "updated_at",
        )

    def create(self, validated_data):
        try:
            return create_coupon_sync(validated_data)
        except DjangoValidationError as exc:
            raise ValidationError(
                exc.message_dict
            ) from exc

    def update(self, instance, validated_data):
        try:
            return update_coupon_sync(instance, validated_data)
        except DjangoValidationError as exc:
            raise ValidationError(
                exc.message_dict
            ) from exc

    async def acreate(self, validated_data):
        try:
            return await CreateCoupon()(validated_data=validated_data)
        except DjangoValidationError as exc:
            raise ValidationError(exc.message_dict) from exc

    async def aupdate(self, instance, validated_data):
        try:
            return await UpdateCoupon()(
                instance=instance,
                validated_data=validated_data,
            )
        except DjangoValidationError as exc:
            raise ValidationError(exc.message_dict) from exc
