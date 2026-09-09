from django.db import transaction

from accounts.services.employee_shift import require_open_shift
from auditlog.services import record_event
from common.exceptions import InsufficientStock, InvalidBusinessOperation
from common.observability import log_operation
from inventory.models import StockLocation, StockMovement, StockMovementItem
from inventory.services.stock_balance import StockBalanceService


@transaction.atomic
def transfer_stock(*, source_id, destination_id, items, created_by, reference=""):
    if source_id == destination_id:
        raise InvalidBusinessOperation("Source and destination must be different.")
    if not items:
        raise InvalidBusinessOperation("Transfer must contain at least one item.")

    shift = require_open_shift(created_by)
    visible_locations = StockLocation.objects.visible_to(created_by).filter(is_active=True)
    location_map = {
        location.pk: location
        for location in visible_locations.select_for_update().filter(pk__in=(source_id, destination_id)).order_by("pk")
    }
    source = location_map.get(source_id)
    destination = location_map.get(destination_id)
    if source is None or destination is None:
        raise InvalidBusinessOperation("Source or destination location is not accessible.")

    if shift is not None and (source.site_id != shift.site_id or destination.site_id != shift.site_id):
        raise InvalidBusinessOperation("A site-scoped employee can only transfer stock within the current shift site.")

    product_ids = [item["product"].pk for item in items]
    if len(product_ids) != len(set(product_ids)):
        raise InvalidBusinessOperation("A product can appear only once in a transfer.")

    movement = StockMovement.objects.create(
        movement_type=StockMovement.MovementType.TRANSFER,
        source_location=source,
        destination_location=destination,
        shift=shift,
        created_by_id=created_by.pk,
        reference=reference,
    )
    for item in sorted(items, key=lambda value: value["product"].pk):
        product = item["product"]
        quantity = item["quantity"]
        try:
            balance = StockBalanceService.decrease(location=source, product=product, quantity=quantity)
        except ValueError as exc:
            raise InsufficientStock(f"Insufficient stock for {product.name} in {source.name}.") from exc
        unit_cost = getattr(balance, "_removed_unit_cost", product.purchase_price)
        StockBalanceService.increase(location=destination, product=product, quantity=quantity, unit_cost=unit_cost)
        StockMovementItem.objects.create(movement=movement, product=product, quantity=quantity, unit_cost=unit_cost)

    log_operation("inventory.transfer", user=created_by.pk, source=source.pk, destination=destination.pk, item_count=len(items), movement=movement.pk)
    record_event(
        action="inventory.transfer",
        entity_type="StockMovement",
        entity_id=movement.pk,
        actor_id=created_by.pk,
        metadata={
            "source_location_id": source.pk,
            "destination_location_id": destination.pk,
            "site_id": shift.site_id if shift else source.site_id,
            "shift_id": shift.pk if shift else None,
            "item_count": len(items),
            "reference": reference,
        },
    )
    return movement


class TransferStock:
    def __call__(self, *, source_id, destination_id, items, created_by, reference=""):
        return transfer_stock(source_id=source_id, destination_id=destination_id, items=items, created_by=created_by, reference=reference)
