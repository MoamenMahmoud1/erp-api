"""Application service for updating coupons."""

from asgiref.sync import sync_to_async


def update_coupon_sync(instance, validated_data):
    """Apply validated fields and preserve Coupon.save() validation."""
    for attribute, value in validated_data.items():
        setattr(instance, attribute, value)
    instance.save()
    return instance


class UpdateCoupon:
    """Update a coupon off the ASGI event loop."""

    async def __call__(self, *, instance, validated_data):
        return await sync_to_async(
            update_coupon_sync,
            thread_sensitive=True,
        )(instance, validated_data)
