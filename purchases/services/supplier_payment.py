from decimal import Decimal

from django.db import transaction
from django.db.models import Prefetch

from accounts.services.employee_shift import operation_context
from accounting.services import get_default_company, post_supplier_payment
from auditlog.services import record_event
from common.exceptions import InvalidBusinessOperation, InvalidMoney
from common.money import quantize_money
from common.observability import log_operation
from purchases.models import Purchase, PurchaseReturnItem, SupplierPayment, SupplierPaymentAllocation


class SupplierPaymentError(InvalidBusinessOperation):
    pass


class SupplierPaymentOverpaymentError(SupplierPaymentError):
    pass


def _allocated_amount(purchase):
    return sum((allocation.total_amount for allocation in purchase.supplier_payment_allocations.all()), Decimal("0"))


@transaction.atomic
def pay_supplier(*, supplier, cash_amount, transfer_amount, paid_by_id, reference="", actor=None):
    cash = quantize_money(cash_amount)
    transfer = quantize_money(transfer_amount)
    if cash < 0 or transfer < 0:
        raise InvalidMoney("Cash and transfer amounts must not be negative.")

    total_received = quantize_money(cash + transfer)
    if total_received <= 0:
        raise InvalidMoney("Supplier payment must be greater than zero.")

    site = None
    shift = None
    if actor is not None:
        _employee, site, shift = operation_context(actor)
    site_id = site.pk if site else None

    purchases = (
        Purchase.objects.filter(supplier=supplier, status=Purchase.Status.CONFIRMED)
        .visible_to(actor) if actor is not None else Purchase.objects.filter(supplier=supplier, status=Purchase.Status.CONFIRMED)
    )
    purchases = purchases.select_for_update().prefetch_related(
        "items",
        "supplier_payment_allocations",
        Prefetch("returns__items", queryset=PurchaseReturnItem.objects.select_related("purchase_item")),
    ).order_by("created_at", "id")

    outstanding = []
    total_outstanding = Decimal("0")
    for purchase in purchases:
        returned = sum(
            (item.unit_price * item.quantity for purchase_return in purchase.returns.all() for item in purchase_return.items.all()),
            Decimal("0"),
        )
        due = quantize_money(purchase.total_amount - returned - _allocated_amount(purchase))
        if due > 0:
            outstanding.append((purchase, due))
            total_outstanding += due

    if not outstanding:
        raise SupplierPaymentError("The supplier has no outstanding confirmed purchases.")
    if total_received > total_outstanding:
        raise SupplierPaymentOverpaymentError("The payment exceeds the supplier's outstanding balance.")

    payment = SupplierPayment.objects.create(
        supplier=supplier,
        site_id=site_id,
        shift_id=shift.pk if shift else None,
        paid_by_id=paid_by_id,
        cash_amount=cash,
        transfer_amount=transfer,
        reference=reference,
    )

    cash_remaining, transfer_remaining = cash, transfer
    allocated_purchases = 0
    for purchase, due in outstanding:
        cash_use = min(cash_remaining, due)
        transfer_use = min(transfer_remaining, due - cash_use)
        if cash_use == 0 and transfer_use == 0:
            break
        SupplierPaymentAllocation.objects.create(payment=payment, purchase=purchase, cash_amount=cash_use, transfer_amount=transfer_use)
        allocated_purchases += 1
        cash_remaining -= cash_use
        transfer_remaining -= transfer_use
        if cash_remaining == 0 and transfer_remaining == 0:
            break

    post_supplier_payment(payment=payment, actor_id=paid_by_id, company=get_default_company())
    log_operation("payment.supplier", user=paid_by_id, supplier=supplier.pk, payment=payment.pk, amount=str(payment.total_amount))
    record_event(
        action="payment.supplier",
        entity_type="SupplierPayment",
        entity_id=payment.pk,
        actor_id=paid_by_id,
        metadata={"supplier_id": supplier.pk, "site_id": site_id, "shift_id": payment.shift_id, "allocated_purchases": allocated_purchases, "reference": reference},
    )
    return payment


class PaySupplier:
    def __call__(self, *, supplier, cash_amount, transfer_amount, paid_by_id, reference="", actor=None):
        return pay_supplier(supplier=supplier, cash_amount=cash_amount, transfer_amount=transfer_amount, paid_by_id=paid_by_id, reference=reference, actor=actor)
