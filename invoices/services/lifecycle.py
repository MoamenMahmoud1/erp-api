"""Atomic invoice lifecycle transitions."""

from django.db import transaction

from accounting.services import get_default_company, post_sales_invoice, reverse_source_entry
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
        return (
            queryset.select_for_update(of=("self",))
            .select_related("customer", "coupon", "created_by")
            .prefetch_related("items__product", "payment_allocations", "payment_refunds")
            .get(pk=invoice_id)
        )
    except Invoice.DoesNotExist as exc:
        raise InvoiceNotFound("Invoice not found.") from exc


def sales_source_location(user):
    return (
        StockLocation.objects.filter(
            employee=user,
            location_type=StockLocation.LocationType.SALES_VEHICLE,
            is_active=True,
        )
        .select_for_update()
        .first()
    )


def _record_sale_movement(invoice, source_location):
    movement = StockMovement.objects.create(
        movement_type=StockMovement.MovementType.SALE,
        source_location=source_location,
        created_by=invoice.created_by,
        reference=f"Invoice #{invoice.pk}",
    )
    for item in sorted(invoice.items.select_related("product"), key=lambda value: value.product_id):
        try:
            StockBalanceService.decrease(location=source_location, product=item.product, quantity=item.quantity)
        except ValueError as exc:
            raise InsufficientStock(
                f"Insufficient stock for {item.product.name} in {source_location.name}."
            ) from exc
        StockMovementItem.objects.create(movement=movement, product=item.product, quantity=item.quantity)
    return movement


@transaction.atomic
def confirm_invoice(invoice_id, actor=None):
    invoice = load_invoice_for_update(invoice_id, actor)
    if invoice.status != Invoice.Status.DRAFT:
        raise InvalidStateTransition("Only a draft invoice can be confirmed.")
    source = sales_source_location(invoice.created_by)
    if source is None:
        raise InvalidBusinessOperation("The invoice creator has no active sales location from which to fulfill this sale.")
    _record_sale_movement(invoice, source)
    company = get_default_company()
    post_sales_invoice(invoice=invoice, actor_id=invoice.created_by_id, company=company)
    invoice.status = Invoice.Status.CONFIRMED
    invoice.save(update_fields=("status", "updated_at"))
    log_operation("invoice.confirm", user=invoice.created_by_id, invoice=invoice.pk)
    return invoice


@transaction.atomic
def cancel_invoice(invoice_id, actor=None):
    invoice = load_invoice_for_update(invoice_id, actor)
    if invoice.status not in (Invoice.Status.DRAFT, Invoice.Status.CONFIRMED):
        raise InvalidStateTransition(f"Cannot cancel an invoice in state {invoice.status}.")
    if invoice.net_paid_amount > 0:
        raise InvalidStateTransition("A paid invoice must be fully refunded before it can be cancelled.")

    if invoice.status == Invoice.Status.CONFIRMED:
        sale = (
            StockMovement.objects.filter(
                reference=f"Invoice #{invoice.pk}",
                movement_type=StockMovement.MovementType.SALE,
            )
            .select_related("source_location")
            .first()
        )
        if sale is None or sale.source_location is None:
            raise InvalidBusinessOperation("Cannot reverse sale: no original SALE movement found for this invoice.")
        movement = StockMovement.objects.create(
            movement_type=StockMovement.MovementType.SALEABLE_RETURN,
            destination_location=sale.source_location,
            created_by=invoice.created_by,
            reference=f"Cancel Invoice #{invoice.pk}",
        )
        for item in sorted(invoice.items.select_related("product"), key=lambda value: value.product_id):
            StockBalanceService.increase(location=sale.source_location, product=item.product, quantity=item.quantity)
            StockMovementItem.objects.create(movement=movement, product=item.product, quantity=item.quantity)

        original_entry = (
            __import__("accounting.models", fromlist=["JournalEntry"]).JournalEntry.objects
            .filter(
                company=get_default_company(),
                source_type="invoice.sale",
                source_id=invoice.pk,
                status=__import__("accounting.models", fromlist=["JournalEntry"]).JournalEntry.Status.POSTED,
            )
            .prefetch_related("lines")
            .first()
        )
        if original_entry is None:
            raise InvalidBusinessOperation("Cannot reverse sale: accounting entry is missing.")
        reverse_source_entry(
            source_entry=original_entry,
            actor_id=invoice.created_by_id,
            source_type="invoice.sale",
            source_id=invoice.pk,
            company=get_default_company(),
        )

    invoice.status = Invoice.Status.CANCELLED
    invoice.save(update_fields=("status", "updated_at"))
    log_operation("invoice.cancel", user=invoice.created_by_id, invoice=invoice.pk)
    return invoice


# Backward-compatible internal aliases retained for existing tests/callers.
def _record_sale_movement_sync(invoice, source_location):
    return _record_sale_movement(invoice, source_location)


def _cancel_invoice_sync(invoice_id, actor=None):
    return cancel_invoice(invoice_id, actor)


class ConfirmInvoice:
    def __call__(self, invoice_id, actor=None):
        return confirm_invoice(invoice_id, actor)


class CancelInvoice:
    def __call__(self, invoice_id, actor=None):
        return cancel_invoice(invoice_id, actor)
