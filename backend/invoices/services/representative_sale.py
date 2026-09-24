from decimal import Decimal

from django.db import transaction

from accounts.services.employee_shift import require_open_shift
from common.exceptions import InsufficientStock, InvalidBusinessOperation
from common.money import quantize_money
from inventory.models import StockBalance, StockLocation
from inventory.services.stock_balance import StockBalanceService
from invoices.services.create import CreateInvoice
from invoices.services.lifecycle import ConfirmInvoice
from payments.services.collection import collect


@transaction.atomic
def create_representative_sale(*, customer, items, payment_method, payment_amount, representative):
    shift = require_open_shift(representative)
    if shift is None or shift.vehicle_id is None:
        raise InvalidBusinessOperation("An open representative shift with an assigned vehicle is required.")

    vehicle = (
        StockLocation.objects.select_for_update()
        .filter(
            pk=shift.vehicle_id,
            employee_id=representative.pk,
            location_type=StockLocation.LocationType.SALES_VEHICLE,
            is_active=True,
            site_id=shift.site_id,
        )
        .first()
    )
    if vehicle is None:
        raise InvalidBusinessOperation("The current shift vehicle is not available.")

    normalized_items = []
    for item in items:
        product = item["product"]
        quantity = int(item["quantity"])
        balance = (
            StockBalance.objects
            .select_for_update()
            .filter(location=vehicle, product=product)
            .first()
        )
        if balance is None or balance.quantity < quantity:
            available = balance.quantity if balance else 0
            raise InsufficientStock(
                f"Insufficient stock for {product.name} in {vehicle.name}: requested {quantity}, available {available}."
            )
        normalized_items.append({"product": product, "quantity": quantity})

    invoice = CreateInvoice()(created_by=representative, validated_data={
        "customer": customer,
        "items": normalized_items,
        "site": shift.site,
        "shift": shift,
    })
    invoice = ConfirmInvoice()(invoice.pk, actor=representative)

    amount = quantize_money(payment_amount)
    if amount < 0:
        raise InvalidBusinessOperation("Payment amount must not be negative.")
    if amount > Decimal(str(invoice.total)):
        raise InvalidBusinessOperation("Payment amount cannot exceed the invoice total.")

    payment = None
    if amount > 0:
        cash_amount = amount if payment_method == "cash" else Decimal("0")
        transfer_amount = amount if payment_method == "transfer" else Decimal("0")
        payment = collect(
            customer=customer,
            cash_amount=cash_amount,
            transfer_amount=transfer_amount,
            collected_by_id=representative.pk,
            actor=representative,
            invoice_id=invoice.pk,
        )

    return invoice, payment
