from asgiref.sync import sync_to_async
from django.db import transaction

from inventory.models import (
    StockLocation,
    StockMovement,
    StockMovementItem,
)
from inventory.services.stock_balance import StockBalanceService


class TransferStockService:
    @staticmethod
    @transaction.atomic
    def execute(
        *,
        source: StockLocation,
        destination: StockLocation,
        items,
        created_by,
        reference="",
    ):
        if source.pk == destination.pk:
            raise ValueError(
                "Source and destination must be different."
            )

        items = list(items)

        if not items:
            raise ValueError(
                "Transfer must contain at least one item."
            )

        movement = StockMovement.objects.create(
            movement_type=StockMovement.MovementType.TRANSFER,
            source_location=source,
            destination_location=destination,
            created_by=created_by,
            reference=reference,
        )

        for item in items:
            product = item["product"]
            quantity = item["quantity"]

            if quantity <= 0:
                raise ValueError(
                    "Quantity must be greater than zero."
                )

            StockBalanceService.decrease(
                location=source,
                product=product,
                quantity=quantity,
            )

            StockBalanceService.increase(
                location=destination,
                product=product,
                quantity=quantity,
            )

            StockMovementItem.objects.create(
                movement=movement,
                product=product,
                quantity=quantity,
            )

        return movement

    @staticmethod
    async def aexecute(
        *,
        source: StockLocation,
        destination: StockLocation,
        items,
        created_by,
        reference="",
    ):
        return await sync_to_async(
            TransferStockService.execute,
            thread_sensitive=True,
        )(
            source=source,
            destination=destination,
            items=items,
            created_by=created_by,
            reference=reference,
        )