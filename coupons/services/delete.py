"""Protected deletion service for coupons."""

from asgiref.sync import sync_to_async
from django.db import transaction
from django.db.models import ProtectedError

from common.exceptions import InvalidBusinessOperation


def delete_coupon_sync(instance):
    """Delete a coupon, translating invoice protection into a domain error."""
    try:
        with transaction.atomic():
            instance.delete()
    except ProtectedError as exc:
        raise InvalidBusinessOperation(
            "This coupon cannot be deleted because it is used by an invoice."
        ) from exc


class DeleteCoupon:
    """Delete a coupon without allowing protected financial history to change."""

    async def __call__(self, *, instance):
        return await sync_to_async(
            delete_coupon_sync,
            thread_sensitive=True,
        )(instance)
