from django.db import transaction

from accounting.services import get_default_company, post_purchase
from auditlog.services import record_event
from common.exceptions import InvalidBusinessOperation, InvalidStateTransition
from inventory.models import StockLocation, StockMovement, StockMovementItem
from inventory.services.stock_balance import StockBalanceService
from purchases.models import Purchase


class ConfirmPurchaseService:
    @staticmethod
    @transaction.atomic
    def execute(*, purchase_id, actor):
        try:
            purchase = (
                Purchase.objects.visible_to(actor)
                .select_for_update()
                .prefetch_related("items__product")
                .get(pk=purchase_id)
            )
        except Purchase.DoesNotExist as exc:
            raise InvalidBusinessOperation("Purchase not found or not accessible.") from exc

        if purchase.status != Purchase.Status.DRAFT:
            raise InvalidStateTransition("Only draft purchases can be confirmed.")
        items = list(purchase.items.all())
        if not items:
            raise InvalidBusinessOperation("Purchase must contain at least one item.")

        warehouse = (
            StockLocation.objects.filter(
                location_type=StockLocation.LocationType.MAIN_WAREHOUSE,
                is_active=True,
            )
            .select_for_update()
            .first()
        )
        if warehouse is None:
            raise InvalidBusinessOperation("Active main warehouse does not exist.")

        movement = StockMovement.objects.create(
            movement_type=StockMovement.MovementType.PURCHASE,
            destination_location=warehouse,
            created_by=actor,
            reference=purchase.reference,
        )
        for item in sorted(items, key=lambda value: value.product_id):
            StockBalanceService.increase(
                location=warehouse,
                product=item.product,
                quantity=item.quantity,
                unit_cost=item.unit_purchase_price,
            )
            StockMovementItem.objects.create(
                movement=movement,
                product=item.product,
                quantity=item.quantity,
                unit_cost=item.unit_purchase_price,
            )

        post_purchase(
            purchase=purchase,
            actor_id=actor.pk,
            company=get_default_company(),
        )
        purchase.status = Purchase.Status.CONFIRMED
        purchase.save(update_fields=("status", "updated_at"))
        record_event(
            action="purchase.confirm",
            entity_type="Purchase",
            entity_id=purchase.pk,
            actor_id=actor.pk,
            metadata={"warehouse_id": warehouse.pk, "stock_movement_id": movement.pk},
        )
        return purchase
