"""Atomic invoice lifecycle transitions."""

from django.db import transaction

from accounts.services.employee_shift import require_open_shift
from accounting.models import JournalEntry
from accounting.services import get_default_company, post_sales_invoice, reverse_source_entry
from auditlog.services import record_event
from common.exceptions import InsufficientStock, InvalidBusinessOperation, InvalidStateTransition
from common.observability import log_operation
from inventory.models import StockLocation, StockMovement, StockMovementItem
from inventory.services.stock_balance import StockBalanceService
from invoices.models import Invoice


class InvoiceNotFound(InvalidBusinessOperation):
    pass


def load_invoice_for_update(invoice_id, actor=None):
    queryset = Invoice.objects.visible_to(actor) if actor is not None else Invoice.objects
    try:
        return queryset.select_for_update(of=("self",)).select_related("customer", "coupon", "created_by", "site", "shift").prefetch_related("items__product", "payment_allocations", "payment_refunds").get(pk=invoice_id)
    except Invoice.DoesNotExist as exc:
        raise InvoiceNotFound("Invoice not found.") from exc


def _required_shift(actor, invoice=None):
    if actor is None:
        return None
    shift = require_open_shift(actor)
    if shift is not None and invoice is not None and invoice.site_id != shift.site_id:
        raise InvalidBusinessOperation("The invoice belongs to a different site than the current shift.")
    return shift


def sales_source_location(invoice, shift=None):
    if shift is not None and shift.vehicle_id:
        return StockLocation.objects.select_for_update().filter(
            pk=shift.vehicle_id,
            site_id=invoice.site_id,
            location_type=StockLocation.LocationType.SALES_VEHICLE,
            is_active=True,
        ).first()

    queryset = StockLocation.objects.filter(
        employee=invoice.created_by,
        location_type=StockLocation.LocationType.SALES_VEHICLE,
        is_active=True,
    )
    if invoice.site_id:
        queryset = queryset.filter(site_id=invoice.site_id)
    return queryset.select_for_update().first()


def _record_sale_movement(invoice, source_location, shift=None):
    movement = StockMovement.objects.create(
        movement_type=StockMovement.MovementType.SALE,
        source_location=source_location,
        shift=shift,
        created_by=invoice.created_by,
        reference=f"Invoice #{invoice.pk}",
    )
    for item in sorted(invoice.items.select_related("product"), key=lambda value: value.product_id):
        try:
            balance = StockBalanceService.decrease(location=source_location, product=item.product, quantity=item.quantity)
        except ValueError as exc:
            raise InsufficientStock(f"Insufficient stock for {item.product.name} in {source_location.name}.") from exc
        unit_cost = getattr(balance, "_removed_unit_cost", item.product.purchase_price)
        if item.cost_price != unit_cost:
            item.cost_price = unit_cost
            item.save(update_fields=("cost_price",))
        StockMovementItem.objects.create(movement=movement, product=item.product, quantity=item.quantity, unit_cost=unit_cost)
    return movement


@transaction.atomic
def confirm_invoice(invoice_id, actor=None):
    invoice = load_invoice_for_update(invoice_id, actor)
    if invoice.status != Invoice.Status.DRAFT:
        raise InvalidStateTransition("Only a draft invoice can be confirmed.")
    shift = _required_shift(actor, invoice)
    if shift is not None and invoice.shift_id not in (None, shift.pk):
        raise InvalidBusinessOperation("The invoice was created in a different shift.")
    source = sales_source_location(invoice, shift=shift)
    if source is None:
        raise InvalidBusinessOperation("The invoice creator has no active sales location for this branch.")
    for item in invoice.items.select_related("product"):
        if item.cost_price is None:
            item.cost_price = item.product.purchase_price
            item.save(update_fields=("cost_price",))
    movement = _record_sale_movement(invoice, source, shift=shift or invoice.shift)
    company = get_default_company()
    post_sales_invoice(invoice=invoice, actor_id=invoice.created_by_id, company=company)
    if shift is not None and invoice.shift_id is None:
        invoice.shift = shift
    invoice.status = Invoice.Status.CONFIRMED
    invoice.save(update_fields=("status", "shift", "updated_at"))
    log_operation("invoice.confirm", user=invoice.created_by_id, invoice=invoice.pk)
    record_event(action="invoice.confirm", entity_type="Invoice", entity_id=invoice.pk, actor_id=invoice.created_by_id, metadata={"status": invoice.status, "stock_location_id": source.pk, "site_id": invoice.site_id, "shift_id": movement.shift_id})
    return invoice


@transaction.atomic
def cancel_invoice(invoice_id, actor=None):
    invoice = load_invoice_for_update(invoice_id, actor)
    if invoice.status not in (Invoice.Status.DRAFT, Invoice.Status.CONFIRMED):
        raise InvalidStateTransition(f"Cannot cancel an invoice in state {invoice.status}.")
    shift = _required_shift(actor, invoice)
    if invoice.net_paid_amount > 0:
        raise InvalidStateTransition("A paid invoice must be fully refunded before it can be cancelled.")
    if invoice.status == Invoice.Status.CONFIRMED:
        sale = StockMovement.objects.filter(reference=f"Invoice #{invoice.pk}", movement_type=StockMovement.MovementType.SALE).select_related("source_location").prefetch_related("items").first()
        if sale is None or sale.source_location is None:
            raise InvalidBusinessOperation("Cannot reverse sale: no original SALE movement found for this invoice.")
        sale_costs = {item.product_id: item.unit_cost for item in sale.items.all()}
        movement = StockMovement.objects.create(movement_type=StockMovement.MovementType.SALEABLE_RETURN, destination_location=sale.source_location, shift=shift or invoice.shift, created_by=invoice.created_by, reference=f"Cancel Invoice #{invoice.pk}")
        for item in sorted(invoice.items.select_related("product"), key=lambda value: value.product_id):
            unit_cost = sale_costs.get(item.product_id) or item.cost_price or item.product.purchase_price
            StockBalanceService.increase(location=sale.source_location, product=item.product, quantity=item.quantity, unit_cost=unit_cost)
            StockMovementItem.objects.create(movement=movement, product=item.product, quantity=item.quantity, unit_cost=unit_cost)
        original_entry = JournalEntry.objects.filter(company=get_default_company(), source_type="invoice.sale", source_id=invoice.pk, status=JournalEntry.Status.POSTED).prefetch_related("lines").first()
        if original_entry is None:
            raise InvalidBusinessOperation("Cannot reverse sale: accounting entry is missing.")
        reverse_source_entry(source_entry=original_entry, actor_id=invoice.created_by_id, source_type="invoice.sale", source_id=invoice.pk, company=get_default_company())
    invoice.status = Invoice.Status.CANCELLED
    invoice.save(update_fields=("status", "updated_at"))
    log_operation("invoice.cancel", user=invoice.created_by_id, invoice=invoice.pk)
    record_event(action="invoice.cancel", entity_type="Invoice", entity_id=invoice.pk, actor_id=invoice.created_by_id, metadata={"status": invoice.status, "site_id": invoice.site_id, "shift_id": (shift.pk if shift else invoice.shift_id)})
    return invoice


class ConfirmInvoice:
    def __call__(self, invoice_id, actor=None):
        return confirm_invoice(invoice_id, actor)


class CancelInvoice:
    def __call__(self, invoice_id, actor=None):
        return cancel_invoice(invoice_id, actor)
