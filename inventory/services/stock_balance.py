from decimal import Decimal

from django.db import IntegrityError, transaction
from django.db.models import F

from common.money import quantize_money
from inventory.models import StockBalance


class StockBalanceService:
    @staticmethod
    @transaction.atomic
    def increase(*, location, product, quantity, unit_cost=None):
        if quantity <= 0:
            raise ValueError("Quantity must be greater than zero.")
        if unit_cost is None:
            unit_cost = product.purchase_price
        unit_cost = quantize_money(unit_cost)
        if unit_cost < 0:
            raise ValueError("Unit cost must not be negative.")

        added_cost = quantize_money(unit_cost * quantity)
        updated = (
            StockBalance.objects
            .filter(location=location, product=product)
            .update(
                quantity=F("quantity") + quantity,
                total_cost=F("total_cost") + added_cost,
            )
        )

        if updated == 0:
            try:
                with transaction.atomic():
                    StockBalance.objects.create(
                        location=location,
                        product=product,
                        quantity=quantity,
                        total_cost=added_cost,
                    )
            except IntegrityError:
                StockBalance.objects.filter(
                    location=location,
                    product=product,
                ).update(
                    quantity=F("quantity") + quantity,
                    total_cost=F("total_cost") + added_cost,
                )

        return StockBalance.objects.get(location=location, product=product)

    @staticmethod
    @transaction.atomic
    def decrease(*, location, product, quantity):
        if quantity <= 0:
            raise ValueError("Quantity must be greater than zero.")

        balance = (
            StockBalance.objects
            .select_for_update()
            .filter(location=location, product=product)
            .first()
        )

        if balance is None or balance.quantity < quantity:
            raise ValueError("Insufficient stock.")

        average_unit_cost = balance.average_unit_cost
        if balance.total_cost == 0 and product.purchase_price:
            average_unit_cost = quantize_money(product.purchase_price)
            balance.total_cost = quantize_money(balance.quantity * average_unit_cost)

        removed_cost = quantize_money(average_unit_cost * quantity)
        balance.quantity -= quantity
        balance.total_cost = max(Decimal("0.00"), balance.total_cost - removed_cost)
        if balance.quantity == 0:
            balance.total_cost = Decimal("0.00")
        balance.save(update_fields=["quantity", "total_cost", "updated_at"])
        balance._removed_unit_cost = average_unit_cost
        balance._removed_cost = removed_cost
        return balance

    @staticmethod
    def average_unit_cost(*, location, product):
        balance = (
            StockBalance.objects
            .filter(location=location, product=product)
            .first()
        )
        if balance is None:
            raise ValueError("Stock balance does not exist.")
        if balance.total_cost == 0 and balance.quantity and product.purchase_price:
            return quantize_money(product.purchase_price)
        return quantize_money(balance.average_unit_cost)
