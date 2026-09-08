from django.db import transaction

from accounting.services import get_default_company, post_purchase_return
from auditlog.services import record_event
from common.exceptions import InsufficientStock, InvalidBusinessOperation
from inventory.models import StockLocation, StockMovement, StockMovementItem
from inventory.services.stock_balance import StockBalanceService
from purchases.models import Purchase, PurchaseReturn, PurchaseReturnItem


@transaction.atomic
def return_purchase(*, purchase_id, items, created_by_id, reason="", actor=None):
    purchases = Purchase.objects.visible_to(actor) if actor is not None else Purchase.objects
    try:
        purchase = purchases.select_for_update().prefetch_related("items__return_items").get(pk=purchase_id)
    except Purchase.DoesNotExist as exc:
        raise InvalidBusinessOperation("Purchase not found or not accessible.") from exc

    if purchase.status != Purchase.Status.CONFIRMED:
        raise InvalidBusinessOperation("Only confirmed purchases can be returned.")
    if not items:
        raise InvalidBusinessOperation("A purchase return must contain at least one item.")

    lines = {item.pk: item for item in purchase.items.all()}
    seen, cleaned = set(), []
    for data in items:
        line = lines.get(data["purchase_item"].pk)
        quantity = data["quantity"]
        if line is None or line.pk in seen:
            raise InvalidBusinessOperation("Return items must belong to the target purchase and be unique.")
        seen.add(line.pk)
        already_returned = sum(item.quantity for item in line.return_items.all())
        if quantity > line.quantity - already_returned:
            raise InvalidBusinessOperation("Return quantity exceeds the remaining purchased quantity.")
        cleaned.append((line, quantity))

    warehouse = StockLocation.objects.select_for_update().filter(
        location_type=StockLocation.LocationType.MAIN_WAREHOUSE,
        is_active=True,
    ).first()
    if warehouse is None:
        raise InvalidBusinessOperation("Active main warehouse does not exist.")

    purchase_return = PurchaseReturn.objects.create(purchase=purchase, created_by_id=created_by_id, reason=reason)
    movement = StockMovement.objects.create(
        movement_type=StockMovement.MovementType.PURCHASE_RETURN,
        source_location=warehouse,
        created_by_id=created_by_id,
        reference=f"Return Purchase #{purchase.pk}",
    )
    for line, quantity in cleaned:
        try:
            balance = StockBalanceService.decrease(
                location=warehouse,
                product=line.product,
                quantity=quantity,
            )
        except ValueError as exc:
            raise InsufficientStock(f"Insufficient stock for {line.product.name} in {warehouse.name}.") from exc
        unit_cost = getattr(balance, "_removed_unit_cost", line.unit_purchase_price)
        PurchaseReturnItem.objects.create(
            purchase_return=purchase_return,
            purchase_item=line,
            quantity=quantity,
            unit_price=line.unit_purchase_price,
        )
        StockMovementItem.objects.create(
            movement=movement,
            product=line.product,
            quantity=quantity,
            unit_cost=unit_cost,
        )

    post_purchase_return(purchase_return=purchase_return, actor_id=created_by_id, company=get_default_company())
    record_event(
        action="purchase.return",
        entity_type="PurchaseReturn",
        entity_id=purchase_return.pk,
        actor_id=created_by_id,
        metadata={"purchase_id": purchase.pk, "stock_movement_id": movement.pk, "reason": reason},
    )
    return purchase_return


class ReturnPurchase:
    def __call__(self, *, purchase_id, items, created_by_id, reason="", actor=None):
        return return_purchase(purchase_id=purchase_id, items=items, created_by_id=created_by_id, reason=reason, actor=actor)
