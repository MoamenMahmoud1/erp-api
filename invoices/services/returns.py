from decimal import Decimal

from django.db import transaction

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
        already_returned = sum(item.quantity for item in line.return_items.all())
        if quantity > line.quantity - already_returned:
            raise InvalidBusinessOperation("Return quantity exceeds the remaining sold quantity.")
        cleaned.append((line, quantity))
        returned_subtotal += line.unit_price * quantity
    return cleaned, quantize_money(returned_subtotal)


@transaction.atomic
def create_sales_return(*, invoice_id, items, created_by_id, reason="", actor=None):
    invoice_qs = Invoice.objects
    if actor is not None:
        invoice_qs = invoice_qs.visible_to(actor)
    invoice = invoice_qs.select_for_update().prefetch_related("items__return_items").get(pk=invoice_id)
    if invoice.status != Invoice.Status.PAID:
        raise InvalidBusinessOperation("Sales returns require a paid invoice and a refund.")

    cleaned, returned_subtotal = _validate_return_items(invoice, items)
    refund_amount = (
        Decimal("0")
        if invoice.subtotal == 0
        else quantize_money(returned_subtotal * invoice.total / invoice.subtotal)
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
        .first()
    )
    if sale is None or sale.source_location is None:
        raise InvalidBusinessOperation("Cannot return sale: original sale movement was not found.")

    sales_return = InvoiceReturn.objects.create(invoice=invoice, created_by_id=created_by_id, reason=reason)
    movement = StockMovement.objects.create(
        movement_type=StockMovement.MovementType.SALEABLE_RETURN,
        destination_location=sale.source_location,
        created_by_id=created_by_id,
        reference=f"Return Invoice #{invoice.pk}",
    )
    for line, quantity in cleaned:
        StockBalanceService.increase(location=sale.source_location, product=line.product, quantity=quantity)
        InvoiceReturnItem.objects.create(invoice_return=sales_return, invoice_item=line, quantity=quantity, unit_price=line.unit_price)
        StockMovementItem.objects.create(movement=movement, product=line.product, quantity=quantity)
    return sales_return


class CreateSalesReturn:
    def __call__(self, *, invoice_id, items, created_by_id, reason="", actor=None):
        return create_sales_return(invoice_id=invoice_id, items=items, created_by_id=created_by_id, reason=reason, actor=actor)
