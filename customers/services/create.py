"""Application service for creating customers."""

from asgiref.sync import sync_to_async

from customers.models import Customer


def create_customer_sync(validated_data):
    """Persist a customer in a synchronous ORM boundary."""
    return Customer.objects.create(**validated_data)


class CreateCustomer:
    """Create a customer without blocking the ASGI event loop."""

    async def __call__(self, *, validated_data):
        return await sync_to_async(
            create_customer_sync,
            thread_sensitive=True,
        )(validated_data)
