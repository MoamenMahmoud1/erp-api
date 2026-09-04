from asgiref.sync import sync_to_async
from django.db import IntegrityError, transaction
from django.db.models import F

from inventory.models import StockBalance


class StockBalanceService:
    @staticmethod
    @transaction.atomic
    def increase(*, location, product, quantity):
        if quantity <= 0:
            raise ValueError("Quantity must be greater than zero.")

        # Atomic UPDATE is safe when the balance row already exists.  If it
        # does not, create it and recover from the unique-constraint race.
        # This avoids the read-modify-write race in get_or_create() while
        # preserving correctness when two workers create the first balance
        # concurrently.
        updated = (
            StockBalance.objects
            .filter(location=location, product=product)
            .update(quantity=F("quantity") + quantity)
        )

        if updated == 0:
            try:
                with transaction.atomic():
                    StockBalance.objects.create(
                        location=location,
                        product=product,
                        quantity=quantity,
                    )
            except IntegrityError:
                # Another transaction created the row first. The database
                # unique constraint makes this deterministic; retry as an
                # atomic UPDATE so the increment is not lost.
                StockBalance.objects.filter(
                    location=location,
                    product=product,
                ).update(quantity=F("quantity") + quantity)

        return StockBalance.objects.get(
            location=location,
            product=product,
        )

    @staticmethod
    async def aincrease(*, location, product, quantity):
        return await sync_to_async(
            StockBalanceService.increase,
            thread_sensitive=True,
        )(
            location=location,
            product=product,
            quantity=quantity,
        )

    @staticmethod
    @transaction.atomic
    def decrease(*, location, product, quantity):
        if quantity <= 0:
            raise ValueError("Quantity must be greater than zero.")

        balance = (
            StockBalance.objects
            .select_for_update()
            .filter(
                location=location,
                product=product,
            )
            .first()
        )

        if balance is None or balance.quantity < quantity:
            raise ValueError("Insufficient stock.")

        balance.quantity -= quantity
        balance.save(
            update_fields=["quantity", "updated_at"],
        )

        return balance

    @staticmethod
    async def adecrease(*, location, product, quantity):
        return await sync_to_async(
            StockBalanceService.decrease,
            thread_sensitive=True,
        )(
            location=location,
            product=product,
            quantity=quantity,
        )
