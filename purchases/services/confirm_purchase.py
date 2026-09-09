from django.db import transaction

from accounts.services.employee_shift import require_open_shift
from accounting.services import get_default_company, post_purchase
from auditlog.services import record_event
from common.exceptions import InvalidBusinessOperation, InvalidStateTransition
from inventory.models import InventoryBatch, StockLocation, StockMovement, StockMovementItem
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
                .select_related("site", "shift")
                .prefetch_related("items__product")
                .get(pk=purchase_id)
            )
        except Purchase.DoesNotExist as exc:
            raise InvalidBusinessOperation("Purchase not found or not accessible.") from exc

        if purchase.status != Purchase.Status.DRAFT:
            raise InvalidStateTransition("Only draft purchases can be confirmed.")

        shift = require_open_shift(actor)
        if shift is not None:
            if purchase.site_id != shift.site_id:
                raise InvalidBusinessOperation("The purchase belongs to a different site than the current shift.")
            if purchase.shift_id not in (None, shift.pk):
                raise InvalidBusinessOperation("The purchase was created in a different shift.")

        items = list(purchase.items.all())
        if not items:
            raise InvalidBusinessOperation("Purchase must contain at least one item.")

        warehouse_query = StockLocation.objects.filter(
            location_type=StockLocation.LocationType.MAIN_WAREHOUSE,
            is_active=True,
        )
        if purchase.site_id:
            warehouse_query = warehouse_query.filter(site_id=purchase.site_id)
        warehouses = list(warehouse_query.select_for_update()[:2])
        if not warehouses:
            raise InvalidBusinessOperation("An active main warehouse does not exist for this branch.")
        if len(warehouses) > 1:
            raise InvalidBusinessOperation("The site has more than one active main warehouse.")
        warehouse = warehouses[0]

        movement = StockMovement.objects.create(
            movement_type=StockMovement.MovementType.PURCHASE,
            destination_location=warehouse,
            shift=shift or purchase.shift,
            created_by_id=actor.pk,
            reference=purchase.reference,
        )
        for item in sorted(items, key=lambda value: value.product_id):
            batch = None
            batch_number = (item.batch_number or "").strip()
            if batch_number or item.manufactured_date or item.expiry_date:
                batch, _created = InventoryBatch.objects.get_or_create(
                    product=item.product,
                    batch_number=batch_number or None,
                    defaults={
                        "manufactured_date": item.manufactured_date,
                        "expiry_date": item.expiry_date,
                    },
                )
                if (
                    batch.manufactured_date != item.manufactured_date
                    or batch.expiry_date != item.expiry_date
                ):
                    raise InvalidBusinessOperation(
                        f"Batch {batch.batch_number or batch.pk} for {item.product.name} already exists with different dates."
                    )
            else:
                batch = InventoryBatch.objects.create(product=item.product)

            item.batch = batch
            item.save(update_fields=("batch",))
            StockBalanceService.increase(
                location=warehouse,
                product=item.product,
                quantity=item.quantity,
                unit_cost=item.unit_purchase_price,
                batch=batch,
            )
            StockMovementItem.objects.create(
                movement=movement,
                product=item.product,
                batch=batch,
                quantity=item.quantity,
                unit_cost=item.unit_purchase_price,
            )

        post_purchase(purchase=purchase, actor_id=actor.pk, company=get_default_company())
        if shift is not None and purchase.shift_id is None:
            purchase.shift = shift
        purchase.status = Purchase.Status.CONFIRMED
        purchase.save(update_fields=("status", "shift", "updated_at"))
        record_event(
            action="purchase.confirm",
            entity_type="Purchase",
            entity_id=purchase.pk,
            actor_id=actor.pk,
            metadata={
                "warehouse_id": warehouse.pk,
                "stock_movement_id": movement.pk,
                "site_id": purchase.site_id,
                "shift_id": movement.shift_id,
            },
        )
        return purchase
