"""Application service for deleting customers."""

from asgiref.sync import sync_to_async
from django.db import transaction
from django.db.models import ProtectedError

from common.exceptions import InvalidBusinessOperation


def delete_customer_sync(instance):
    """Delete a customer through the synchronous ORM."""
    try:
        with transaction.atomic():
            instance.delete()
    except ProtectedError as exc:
        raise InvalidBusinessOperation(
            "This customer cannot be deleted because it has financial records."
        ) from exc


class DeleteCustomer:
    """Delete a customer without blocking the ASGI event loop."""

    async def __call__(self, *, instance):
        return await sync_to_async(
            delete_customer_sync,
            thread_sensitive=True,
        )(instance)
