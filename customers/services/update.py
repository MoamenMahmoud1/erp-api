"""Application service for updating customers."""

from asgiref.sync import sync_to_async


def update_customer_sync(instance, validated_data):
    """Apply validated fields through the synchronous ORM."""
    for attribute, value in validated_data.items():
        setattr(instance, attribute, value)
    instance.save()
    return instance


class UpdateCustomer:
    """Update a customer without blocking the ASGI event loop."""

    async def __call__(self, *, instance, validated_data):
        return await sync_to_async(
            update_customer_sync,
            thread_sensitive=True,
        )(instance, validated_data)
