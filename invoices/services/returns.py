from decimal import Decimal

from django.db import transaction

from accounts.services.employee_shift import require_open_shift
from accounting.services import get_default_company, post_sales_return
from auditlog.services import record_event
from common.exceptions import InvalidBusinessOperation
from common.money import quantize_money
from inventory.models import StockMovement, StockMovementItem
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


@transaction.atomic
def create_sales_return(*, invoice_id, items, created_by_id, reason="", actor=None):
    invoice_qs = Invoice.objects.visible_to(actor) if actor is not None else Invoice.objects
    invoice = invoice_qs.select_for_update().prefetch_related("items__return_items").get(pk=invoice_id)
    if invoice.status != Invoice.Status.PAID:
        raise InvalidBusinessOperation("Sales returns require a paid invoice and a refund.")

    shift = require_open_shift(actor) if actor is not None else None
    if shift is not None and invoice.site_id != shift.site_id:
        raise InvalidBusinessOperation("The invoice belongs to a different site than the current shift.")

    cleaned, returned_subtotal = _validate_return_items(invoice, items)
    refund_amount = Decimal("0") if invoice.subtotal == 0 else quantize_money(returned_subtotal * invoice.total / invoice.subtotal)
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
    )

    sale = (
        StockMovement.objects.filter(reference=f"Invoice #{invoice.pk}", movement_type=StockMovement.MovementType.SALE)
        .select_related("source_location")
        .prefetch_related("items")
        .first()
    )
    if sale is None or sale.source_location is None:
        raise InvalidBusinessOperation("Cannot return sale: original sale movement was not found.")
    sale_costs = {item.product_id: item.unit_cost for item in sale.items.all()}

    movement = StockMovement.objects.create(
        movement_type=StockMovement.MovementType.SALEABLE_RETURN,
        destination_location=sale.source_location,
        shift=shift or invoice.shift,
        created_by_id=created_by_id,
        reference=f"Return Invoice #{invoice.pk}",
    )
    for line, quantity in cleaned:
        unit_cost = sale_costs.get(line.product_id) or line.cost_price or line.product.purchase_price
        StockBalanceService.increase(location=sale.source_location, product=line.product, quantity=quantity, unit_cost=unit_cost)
        InvoiceReturnItem.objects.create(invoice_return=sales_return, invoice_item=line, quantity=quantity, unit_price=line.unit_price)
        StockMovementItem.objects.create(movement=movement, product=line.product, quantity=quantity, unit_cost=unit_cost)

    post_sales_return(sales_return=sales_return, actor_id=created_by_id, company=get_default_company())

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
            "site_id": sales_return.site_id,
            "shift_id": sales_return.shift_id,
            "full_return": invoice.status == Invoice.Status.RETURNED,
            "reason": reason,
        },
    )
    return sales_return


class CreateSalesReturn:
    def __call__(self, *, invoice_id, items, created_by_id, reason="", actor=None):
        return create_sales_return(invoice_id=invoice_id, items=items, created_by_id=created_by_id, reason=reason, created_by_id=created_by_id, actor=actor)
