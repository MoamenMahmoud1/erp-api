"""Protected deletion service for coupons."""

from django.db import transaction
from django.db.models import ProtectedError

from common.exceptions import InvalidBusinessOperation


def delete_coupon(instance):
    """Delete a coupon, translating invoice protection into a domain error."""
    try:
        with transaction.atomic():
            instance.delete()
    except ProtectedError as exc:
        raise InvalidBusinessOperation(
            "This coupon cannot be deleted because it is used by an invoice."
        ) from exc


class DeleteCoupon:
    """Synchronous coupon deletion use case."""

    def __call__(self, *, instance):
        return delete_coupon(instance)
