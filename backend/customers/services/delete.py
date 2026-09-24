"""Application service for deleting customers."""

from django.db import transaction
from django.db.models import ProtectedError

from common.exceptions import InvalidBusinessOperation


def delete_customer(instance):
    """Delete a customer without allowing protected financial history to change."""
    try:
        with transaction.atomic():
            instance.delete()
    except ProtectedError as exc:
        raise InvalidBusinessOperation(
            "This customer cannot be deleted because it has financial records."
        ) from exc


class DeleteCustomer:
    """Synchronous customer deletion use case."""

    def __call__(self, *, instance):
        return delete_customer(instance)
