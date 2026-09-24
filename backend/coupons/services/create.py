from coupons.models import Coupon


def create_coupon_sync(validated_data):
    return Coupon.objects.create(**validated_data)


class CreateCoupon:
    def __call__(self, *, validated_data):
        return create_coupon_sync(validated_data)
