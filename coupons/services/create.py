"""Application service for creating coupons."""

from asgiref.sync import sync_to_async

from coupons.models import Coupon


def create_coupon_sync(validated_data):
    """Persist one coupon; model.save() remains the validation authority."""
    return Coupon.objects.create(**validated_data)


class CreateCoupon:
    """Create a coupon off the ASGI event loop."""

    async def __call__(self, *, validated_data):
        return await sync_to_async(
            create_coupon_sync,
            thread_sensitive=True,
        )(validated_data)
