from collections import defaultdict
from decimal import Decimal

from django.db import transaction

from accounts.services.employee_shift import require_open_shift
from accounting.services import get_default_company, post_sales_return
from auditlog.services import record_event
from common.exceptions import InvalidBusinessOperation
from common.money import quantize_money
from inventory.models import StockLocation, StockMovement, StockMovementItem
from inventory.services.source_reference import build_source_reference, find_source_movement
from inventory.services.stock_balance import StockBalanceService
from invoices.models import Invoice, InvoiceReturn, InvoiceReturnItem
from payments.services.refund_invoice import refund_invoice


def _validate_return_items(invoice, items):
    if not items:
        raise InvalidBusinessOperation("A return must contain at least one item.")
    invoice_items = {item.pk: item for item in invoice.items.all()}
    cleaned, returned_subtotal, seen = [], Decimal("0"), set()
    for data in items:
        line = invoice_items.get(data["invoice_item"].pk)
        quantity = data["quantity"]
        if line is None:
            raise InvalidBusinessOperation("A return item must belong to the target invoice.")
        if line.pk in seen:
            raise InvalidBusinessOperation("An invoice line can appear only once in a return.")
        seen.add(line.pk)
        returned = sum(item.quantity for item in line.return_items.all())
        if quantity > line.quantity - returned:
            raise InvalidBusinessOperation("Return quantity exceeds the remaining sold quantity.")
        cleaned.append((line, quantity))
        returned_subtotal += line.unit_price * quantity
    return cleaned, quantize_money(returned_subtotal)


def _is_full_return(invoice, cleaned):
    requested = {line.pk: quantity for line, quantity in cleaned}
    for line in invoice.items.all():
        previously_returned = sum(item.quantity for item in line.return_items.all())
        if previously_returned + requested.get(line.pk, 0) < line.quantity:
            return False
    return True


def _return_allocations(*, invoice_id, sale, product_id, quantity):
    sale_items = [item for item in sale.items.all() if item.product_id == product_id]
    if not sale_items:
        raise InvalidBusinessOperation("Cannot return sale: original product movement was not found.")

    previous_returned = defaultdict(int)
    previous_movements = StockMovementItem.objects.filter(
        movement__reference__startswith=f"source:invoice.return:{invoice_id}",
    )
    for item in previous_movements:
        if item.product_id == product_id:
            previous_returned[item.batch_id] += item.quantity

    allocations = []
    remaining = quantity
    for sale_item in sale_items:
        available = sale_item.quantity - previous_returned[sale_item.batch_id]
        if available <= 0:
            continue
        take = min(remaining, available)
        allocations.append({"batch": sale_item.batch, "quantity": take, "unit_cost": sale_item.unit_cost})
        remaining -= take
        if remaining == 0:
            break
    if remaining:
        raise InvalidBusinessOperation("Return quantity cannot be mapped to the original inventory batches.")
    return allocations


def _resolve_return_shift(*, actor, processing_shift):
    if processing_shift is not None:
        if actor is not None and processing_shift.employee.user_id != actor.pk:
            raise InvalidBusinessOperation("The processing shift does not belong to the acting representative.")
        return processing_shift
    return require_open_shift(actor) if actor is not None else None


def _validate_return_destination(*, destination_location_id, invoice):
    if destination_location_id is None:
        return None
    destination = (
        StockLocation.objects
        .filter(
            pk=destination_location_id,
            location_type=StockLocation.LocationType.MAIN_WAREHOUSE,
            is_active=True,
        )
        .first()
    )
    if destination is None:
        raise InvalidBusinessOperation("The return destination must be an active main warehouse.")
    if invoice.site_id and destination.site_id != invoice.site_id:
        raise InvalidBusinessOperation("The return destination must belong to the invoice site.")
    return destination


def _validate_return_source(*, source_location_id, invoice, shift):
    if source_location_id is None:
        return None
    source = (
        StockLocation.objects
        .filter(
            pk=source_location_id,
            location_type=StockLocation.LocationType.SALES_VEHICLE,
            is_active=True,
        )
        .first()
    )
    if source is None:
        raise InvalidBusinessOperation("The return source must be an active sales vehicle.")
    if invoice.site_id and source.site_id != invoice.site_id:
        raise InvalidBusinessOperation("The return source must belong to the invoice site.")
    if shift is not None and source.pk != shift.vehicle_id:
        raise InvalidBusinessOperation("The return source must match the representative's stored vehicle.")
    if source.employee_id != invoice.created_by_id:
        raise InvalidBusinessOperation("The return source does not belong to the invoice representative.")
    return source


@transaction.atomic
def create_sales_return(
    *,
    invoice_id,
    items,
    created_by_id,
    reason="",
    actor=None,
    processing_shift=None,
    return_destination_location_id=None,
    return_source_location_id=None,
):
    invoice_qs = Invoice.objects.visible_to(actor) if actor is not None else Invoice.objects
    invoice = (
        invoice_qs.select_for_update()
        .prefetch_related("items__return_items", "items__product")
        .get(pk=invoice_id)
    )
    if invoice.status != Invoice.Status.PAID:
        raise InvalidBusinessOperation("Sales returns require a paid invoice and a refund.")

    shift = _resolve_return_shift(actor=actor, processing_shift=processing_shift)
    if shift is not None and invoice.site_id != shift.site_id:
        raise InvalidBusinessOperation("The invoice belongs to a different site than the current shift.")

    destination = _validate_return_destination(
        destination_location_id=return_destination_location_id,
        invoice=invoice,
    )
    source = _validate_return_source(
        source_location_id=return_source_location_id,
        invoice=invoice,
        shift=shift,
    )

    cleaned, returned_subtotal = _validate_return_items(invoice, items)
    refund_amount = (
        Decimal("0")
        if invoice.subtotal == 0
        else quantize_money(returned_subtotal * invoice.total / invoice.subtotal)
    )
    sales_return = InvoiceReturn.objects.create(
        invoice=invoice,
        site_id=shift.site_id if shift else invoice.site_id,
        shift_id=shift.pk if shift else None,
        created_by_id=created_by_id,
        reason=reason,
        refund_amount=refund_amount,
    )
    refund_invoice(
        invoice_id=invoice.pk,
        amount=refund_amount,
        created_by_id=created_by_id,
        reason=reason or f"Sales return for invoice #{invoice.pk}",
        actor=actor,
        processing_shift=processing_shift,
    )

    sale = find_source_movement(
        source_type="invoice.sale",
        source_id=invoice.pk,
        movement_type=StockMovement.MovementType.SALE,
        legacy_reference=f"Invoice #{invoice.pk}",
    )
    if sale is None or sale.source_location is None:
        raise InvalidBusinessOperation("Cannot return sale: original sale movement was not found.")

    return_destination = destination or sale.source_location
    if source is not None and return_destination.pk == source.pk:
        raise InvalidBusinessOperation("Return source and destination must be different locations.")

    movement = StockMovement.objects.create(
        movement_type=(
            StockMovement.MovementType.TRANSFER
            if source is not None
            else StockMovement.MovementType.SALEABLE_RETURN
        ),
        source_location=source,
        destination_location=return_destination,
        shift=shift or invoice.shift,
        created_by_id=created_by_id,
        reference=build_source_reference(
            source_type="invoice.return",
            source_id=invoice.pk,
            label=f"Return #{sales_return.pk} for Invoice #{invoice.pk}",
        ),
    )
    for line, quantity in cleaned:
        if source is not None:
            balance = StockBalanceService.decrease(
                location=source,
                product=line.product,
                quantity=quantity,
            )
            allocations = getattr(balance, "_stock_allocations", None) or [
                {
                    "batch": None,
                    "quantity": quantity,
                    "unit_cost": balance._removed_unit_cost,
                }
            ]
        else:
            allocations = _return_allocations(
                invoice_id=invoice.pk,
                sale=sale,
                product_id=line.product_id,
                quantity=quantity,
            )

        for allocation in allocations:
            unit_cost = allocation["unit_cost"] or line.cost_price or line.product.purchase_price
            StockBalanceService.increase(
                location=return_destination,
                product=line.product,
                quantity=allocation["quantity"],
                unit_cost=unit_cost,
                batch=allocation["batch"],
            )
            StockMovementItem.objects.create(
                movement=movement,
                product=line.product,
                batch=allocation["batch"],
                quantity=allocation["quantity"],
                unit_cost=unit_cost,
            )
        InvoiceReturnItem.objects.create(
            invoice_return=sales_return,
            invoice_item=line,
            quantity=quantity,
            unit_price=line.unit_price,
        )

    post_sales_return(
        sales_return=sales_return,
        actor_id=created_by_id,
        company=get_default_company(),
    )
    if _is_full_return(invoice, cleaned):
        invoice.status = Invoice.Status.RETURNED
        invoice.save(update_fields=("status", "updated_at"))
    record_event(
        action="invoice.return",
        entity_type="InvoiceReturn",
        entity_id=sales_return.pk,
        actor_id=created_by_id,
        metadata={
            "invoice_id": invoice.pk,
            "stock_movement_id": movement.pk,
            "source_location_id": source.pk if source else None,
            "destination_location_id": return_destination.pk,
            "site_id": sales_return.site_id,
            "shift_id": sales_return.shift_id,
            "full_return": invoice.status == Invoice.Status.RETURNED,
            "reason": reason,
        },
    )
    return sales_return


class CreateSalesReturn:
    def __call__(
        self,
        *,
        invoice_id,
        items,
        created_by_id,
        reason="",
        actor=None,
        processing_shift=None,
        return_destination_location_id=None,
        return_source_location_id=None,
    ):
        return create_sales_return(
            invoice_id=invoice_id,
            items=items,
            created_by_id=created_by_id,
            reason=reason,
            actor=actor,
            processing_shift=processing_shift,
            return_destination_location_id=return_destination_location_id,
            return_source_location_id=return_source_location_id,
        )
