from asgiref.sync import sync_to_async
from django.db import transaction

from inventory.models import (
    StockLocation,
    StockMovement,
    StockMovementItem,
)
from inventory.services.stock_balance import StockBalanceService

from purchases.models import Purchase


class ConfirmPurchaseService:
    @staticmethod
    @transaction.atomic
    def execute(*, purchase_id, created_by_id=None, created_by=None):
        if created_by_id is None:
            if created_by is None:
                raise ValueError("created_by_id is required.")
            created_by_id = getattr(created_by, "pk", created_by)

        purchase = (
            Purchase.objects
            .select_for_update()
            .prefetch_related("items__product")
            .get(pk=purchase_id)
        )

        if purchase.status != Purchase.Status.DRAFT:
            raise ValueError(
                "Only draft purchases can be confirmed."
            )

        items = list(purchase.items.all())

        if not items:
            raise ValueError(
                "Purchase must contain at least one item."
            )

        warehouse = (
            StockLocation.objects
            .filter(
                location_type=(
                    StockLocation.LocationType.MAIN_WAREHOUSE
                ),
                is_active=True,
            )
            .order_by("pk")
            .first()
        )

        if warehouse is None:
            raise ValueError(
                "Active main warehouse does not exist."
            )

        movement = StockMovement.objects.create(
            movement_type=StockMovement.MovementType.PURCHASE,
            destination_location=warehouse,
            created_by_id=created_by_id,
            reference=purchase.reference,
        )

        # Always acquire StockBalance rows in deterministic product-id order.
        for item in sorted(items, key=lambda value: value.product_id):
            StockBalanceService.increase(
                location=warehouse,
                product=item.product,
                quantity=item.quantity,
            )

            StockMovementItem.objects.create(
                movement=movement,
                product=item.product,
                quantity=item.quantity,
            )

        purchase.status = Purchase.Status.CONFIRMED
        purchase.save(
            update_fields=["status", "updated_at"],
        )

        return purchase

    @staticmethod
    async def aexecute(*, purchase_id, created_by_id=None, created_by=None):
        return await sync_to_async(
            ConfirmPurchaseService.execute,
            thread_sensitive=True,
        )(
            purchase_id=purchase_id,
            created_by_id=created_by_id,
            created_by=created_by,
        )
