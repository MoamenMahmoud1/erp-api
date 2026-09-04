from asgiref.sync import sync_to_async
from django.db import transaction

from inventory.models import StockBalance


class StockBalanceService:
    @staticmethod
    @transaction.atomic
    def increase(*, location, product, quantity):
        if quantity <= 0:
            raise ValueError("Quantity must be greater than zero.")

        balance, _ = (
            StockBalance.objects
            .select_for_update()
            .get_or_create(
                location=location,
                product=product,
                defaults={"quantity": 0},
            )
        )

        balance.quantity += quantity
        balance.save(
            update_fields=["quantity", "updated_at"],
        )

        return balance

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