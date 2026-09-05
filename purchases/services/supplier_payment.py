from decimal import Decimal

from django.db import transaction
from django.db.models import Prefetch

from accounting.services import get_default_company, post_supplier_payment
from common.exceptions import InvalidBusinessOperation, InvalidMoney
from common.money import quantize_money
from common.observability import log_operation
from purchases.models import (
    Purchase,
    PurchaseReturnItem,
    SupplierPayment,
    SupplierPaymentAllocation,
)


class SupplierPaymentError(InvalidBusinessOperation):
    pass


class SupplierPaymentOverpaymentError(SupplierPaymentError):
    pass


def _purchase_return_total(purchase):
    return sum(
        (item.line_total for item in purchase_return_items(purchase)),
        Decimal("0"),
    )


def purchase_return_items(purchase):
    return (
        PurchaseReturnItem.objects.filter(purchase_return__purchase_id=purchase.pk)
        .select_related("purchase_item")
    )


def _allocated_amount(purchase):
    return sum(
        (allocation.total_amount for allocation in purchase.supplier_payment_allocations.all()),
        Decimal("0"),
    )


@transaction.atomic
def pay_supplier(*, supplier, cash_amount, transfer_amount, paid_by_id, reference="", actor=None):
    cash = quantize_money(cash_amount)
    transfer = quantize_money(transfer_amount)
    if cash < 0 or transfer < 0:
        raise InvalidMoney("Cash and transfer amounts must not be negative.")

    total_received = quantize_money(cash + transfer)
    if total_received <= 0:
        raise InvalidMoney("Supplier payment must be greater than zero.")

    purchases = (
        Purchase.objects.filter(supplier=supplier, status=Purchase.Status.CONFIRMED)
        .select_for_update()
        .prefetch_related(
            "items",
            "supplier_payment_allocations",
            Prefetch(
                "returns__items",
                queryset=PurchaseReturnItem.objects.select_related("purchase_item"),
            ),
        )
        .order_by("created_at", "id")
    )

    outstanding = []
    total_outstanding = Decimal("0")
    for purchase in purchases:
        returned = sum(
            (
                item.unit_price * item.quantity
                for purchase_return in purchase.returns.all()
                for item in purchase_return.items.all()
            ),
            Decimal("0"),
        )
        allocated = _allocated_amount(purchase)
        due = quantize_money(purchase.total_amount - returned - allocated)
        if due > 0:
            outstanding.append((purchase, due))
            total_outstanding += due

    if not outstanding:
        raise SupplierPaymentError("The supplier has no outstanding confirmed purchases.")
    if total_received > total_outstanding:
        raise SupplierPaymentOverpaymentError("The payment exceeds the supplier's outstanding balance.")

    payment = SupplierPayment.objects.create(
        supplier=supplier,
        paid_by_id=paid_by_id,
        cash_amount=cash,
        transfer_amount=transfer,
        reference=reference,
    )

    cash_remaining, transfer_remaining = cash, transfer
    for purchase, due in outstanding:
        cash_use = min(cash_remaining, due)
        transfer_use = min(transfer_remaining, due - cash_use)
        if cash_use == 0 and transfer_use == 0:
            break
        SupplierPaymentAllocation.objects.create(
            payment=payment,
            purchase=purchase,
            cash_amount=cash_use,
            transfer_amount=transfer_use,
        )
        cash_remaining -= cash_use
        transfer_remaining -= transfer_use
        if cash_remaining == 0 and transfer_remaining == 0:
            break

    post_supplier_payment(
        payment=payment,
        actor_id=paid_by_id,
        company=get_default_company(),
    )
    log_operation(
        "payment.supplier",
        user=paid_by_id,
        supplier=supplier.pk,
        payment=payment.pk,
        amount=str(payment.total_amount),
    )
    return payment


class PaySupplier:
    def __call__(self, *, supplier, cash_amount, transfer_amount, paid_by_id, reference="", actor=None):
        return pay_supplier(
            supplier=supplier,
            cash_amount=cash_amount,
            transfer_amount=transfer_amount,
            paid_by_id=paid_by_id,
            reference=reference,
            actor=actor,
        )
