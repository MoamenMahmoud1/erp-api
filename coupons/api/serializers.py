from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers

from coupons.models import Coupon
from coupons.services.create import create_coupon_sync
from coupons.services.update import update_coupon_sync


class CouponSerializer(serializers.ModelSerializer):
    class Meta:
        model = Coupon
        fields = "__all__"
        read_only_fields = ("id", "created_at", "updated_at")

    def create(self, validated_data):
        try:
            return create_coupon_sync(validated_data)
        except DjangoValidationError as exc:
            raise serializers.ValidationError(exc.message_dict) from exc

    def update(self, instance, validated_data):
        try:
            return update_coupon_sync(instance, validated_data)
        except DjangoValidationError as exc:
            raise serializers.ValidationError(exc.message_dict) from exc
