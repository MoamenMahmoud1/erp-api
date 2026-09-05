from django.db import transaction

from common.exceptions import InvalidBusinessOperation
from inventory.models import StockLocation, StockMovement, StockMovementItem
from inventory.services.stock_balance import StockBalanceService


@transaction.atomic
def transfer_stock(*, source_id, destination_id, items, created_by, reference=""):
    if source_id == destination_id:
        raise InvalidBusinessOperation("Source and destination must be different.")
    if not items:
        raise InvalidBusinessOperation("Transfer must contain at least one item.")

    visible_locations = StockLocation.objects.visible_to(created_by).filter(is_active=True)
    try:
        source = visible_locations.select_for_update().get(pk=source_id)
        destination = visible_locations.select_for_update().get(pk=destination_id)
    except StockLocation.DoesNotExist as exc:
        raise InvalidBusinessOperation("Source or destination location is not accessible.") from exc

    product_ids = [item["product"].pk if hasattr(item["product"], "pk") else item["product"] for item in items]
    if len(product_ids) != len(set(product_ids)):
        raise InvalidBusinessOperation("A product can appear only once in a transfer.")

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
            raise InvalidBusinessOperation("Quantity must be greater than zero.")
        StockBalanceService.decrease(location=source, product=product, quantity=quantity)
        StockBalanceService.increase(location=destination, product=product, quantity=quantity)
        StockMovementItem.objects.create(movement=movement, product=product, quantity=quantity)
    return movement


class TransferStock:
    def __call__(self, *, source_id, destination_id, items, created_by, reference=""):
        return transfer_stock(
            source_id=source_id,
            destination_id=destination_id,
            items=items,
            created_by=created_by,
            reference=reference,
        )
