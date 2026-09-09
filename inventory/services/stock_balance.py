from decimal import Decimal

from django.db import IntegrityError, transaction
from django.db.models import F, Sum
from django.db.models.functions import Coalesce
from django.utils import timezone

from common.money import quantize_money
from inventory.models import StockBalance, StockBatchBalance


class StockBalanceService:
    @staticmethod
    def increase(*, location, product, quantity, unit_cost=None, batch=None):
        if quantity <= 0:
            raise ValueError("Quantity must be greater than zero.")
        if batch is not None and batch.product_id != product.pk:
            raise ValueError("Batch does not belong to product.")
        if unit_cost is None:
            unit_cost = product.purchase_price
        unit_cost = quantize_money(unit_cost)
        if unit_cost < 0:
            raise ValueError("Unit cost must not be negative.")

        added_cost = quantize_money(unit_cost * quantity)
        updated = (
            StockBalance.objects
            .filter(location=location, product=product)
            .update(quantity=F("quantity") + quantity, total_cost=F("total_cost") + added_cost)
        )
        if updated == 0:
            try:
                with transaction.atomic():
                    StockBalance.objects.create(location=location, product=product, quantity=quantity, total_cost=added_cost)
            except IntegrityError:
                StockBalance.objects.filter(location=location, product=product).update(
                    quantity=F("quantity") + quantity,
                    total_cost=F("total_cost") + added_cost,
                )

        if batch is not None:
            batch_updated = (
                StockBatchBalance.objects
                .filter(location=location, batch=batch)
                .update(quantity=F("quantity") + quantity, total_cost=F("total_cost") + added_cost)
            )
            if batch_updated == 0:
                try:
                    with transaction.atomic():
                        StockBatchBalance.objects.create(
                            location=location,
                            batch=batch,
                            quantity=quantity,
                            total_cost=added_cost,
                        )
                except IntegrityError:
                    StockBatchBalance.objects.filter(location=location, batch=batch).update(
                        quantity=F("quantity") + quantity,
                        total_cost=F("total_cost") + added_cost,
                    )

        return StockBalance.objects.get(location=location, product=product)

    @staticmethod
    def _decrease_batch_locked(*, balance, quantity):
        if balance.quantity < quantity:
            raise ValueError("Insufficient batch stock.")
        average_unit_cost = quantize_money(balance.average_unit_cost)
        removed_cost = quantize_money(average_unit_cost * quantity)
        balance.quantity -= quantity
        balance.total_cost = max(Decimal("0.00"), balance.total_cost - removed_cost)
        if balance.quantity == 0:
            balance.total_cost = Decimal("0.00")
        balance.save(update_fields=("quantity", "total_cost", "updated_at"))
        return average_unit_cost, removed_cost

    @staticmethod
    @transaction.atomic
    def decrease_specific_batch(*, location, batch, quantity):
        if quantity <= 0:
            raise ValueError("Quantity must be greater than zero.")
        batch_balance = (
            StockBatchBalance.objects
            .select_for_update()
            .select_related("batch__product")
            .filter(location=location, batch=batch)
            .first()
        )
        if batch_balance is None or batch_balance.quantity < quantity:
            raise ValueError("Insufficient batch stock.")

        average_unit_cost, removed_cost = StockBalanceService._decrease_batch_locked(
            balance=batch_balance,
            quantity=quantity,
        )
        aggregate = StockBalance.objects.select_for_update().get(location=location, product=batch.product)
        if aggregate.quantity < quantity:
            raise ValueError("Aggregate stock is inconsistent with batch stock.")
        aggregate.quantity -= quantity
        aggregate.total_cost = max(Decimal("0.00"), aggregate.total_cost - removed_cost)
        if aggregate.quantity == 0:
            aggregate.total_cost = Decimal("0.00")
        aggregate.save(update_fields=("quantity", "total_cost", "updated_at"))
        return average_unit_cost, removed_cost

    @staticmethod
    @transaction.atomic
    def decrease(*, location, product, quantity):
        if quantity <= 0:
            raise ValueError("Quantity must be greater than zero.")

        aggregate = (
            StockBalance.objects
            .select_for_update()
            .filter(location=location, product=product)
            .first()
        )
        if aggregate is None or aggregate.quantity < quantity:
            raise ValueError("Insufficient stock.")

        allocations = []
        remaining = quantity
        today = timezone.localdate()
        batch_rows = list(
            StockBatchBalance.objects
            .select_for_update()
            .select_related("batch__product")
            .filter(location=location, batch__product=product, quantity__gt=0)
            .filter(batch__expiry_date__isnull=True)
        )
        batch_rows += list(
            StockBatchBalance.objects
            .select_for_update()
            .select_related("batch__product")
            .filter(
                location=location,
                batch__product=product,
                quantity__gt=0,
                batch__expiry_date__gte=today,
            )
        )
        batch_rows.sort(key=lambda row: (row.batch.expiry_date is None, row.batch.expiry_date or today, row.batch_id))

        for batch_balance in batch_rows:
            if remaining <= 0:
                break
            take = min(remaining, batch_balance.quantity)
            unit_cost, removed_cost = StockBalanceService._decrease_batch_locked(balance=batch_balance, quantity=take)
            aggregate.quantity -= take
            aggregate.total_cost = max(Decimal("0.00"), aggregate.total_cost - removed_cost)
            allocations.append({"batch": batch_balance.batch, "quantity": take, "unit_cost": unit_cost, "cost": removed_cost})
            remaining -= take

        if remaining:
            tracked = StockBatchBalance.objects.filter(location=location, batch__product=product).aggregate(
                quantity=Coalesce(Sum("quantity"), 0),
                total_cost=Coalesce(Sum("total_cost"), Decimal("0.00")),
            )
            legacy_quantity = aggregate.quantity - tracked["quantity"]
            legacy_cost = max(Decimal("0.00"), aggregate.total_cost - tracked["total_cost"])
            if legacy_quantity < remaining:
                raise ValueError("Insufficient non-expired stock.")
            average_unit_cost = (
                quantize_money(legacy_cost / Decimal(legacy_quantity))
                if legacy_quantity and legacy_cost
                else quantize_money(product.purchase_price)
            )
            removed_cost = quantize_money(average_unit_cost * remaining)
            aggregate.quantity -= remaining
            aggregate.total_cost = max(Decimal("0.00"), aggregate.total_cost - removed_cost)
            allocations.append({"batch": None, "quantity": remaining, "unit_cost": average_unit_cost, "cost": removed_cost})
            remaining = 0

        if sum(item["quantity"] for item in allocations) != quantity:
            raise ValueError("Stock allocation failed to cover requested quantity.")
        if aggregate.quantity == 0:
            aggregate.total_cost = Decimal("0.00")
        aggregate.save(update_fields=("quantity", "total_cost", "updated_at"))
        aggregate._stock_allocations = allocations
        aggregate._removed_cost = sum((item["cost"] for item in allocations), Decimal("0.00"))
        aggregate._removed_unit_cost = quantize_money(aggregate._removed_cost / Decimal(quantity))
        return aggregate

    @staticmethod
    def average_unit_cost(*, location, product):
        balance = StockBalance.objects.filter(location=location, product=product).first()
        if balance is None:
            raise ValueError("Stock balance does not exist.")
        if balance.total_cost == 0 and balance.quantity and product.purchase_price:
            return quantize_money(product.purchase_price)
        return quantize_money(balance.average_unit_cost)

    @staticmethod
    def batch_stock(*, location=None, product=None, include_empty=False):
        queryset = StockBatchBalance.objects.select_related("location", "batch__product")
        if location is not None:
            queryset = queryset.filter(location=location)
        if product is not None:
            queryset = queryset.filter(batch__product=product)
        if not include_empty:
            queryset = queryset.filter(quantity__gt=0)
        return queryset.order_by("batch__expiry_date", "batch_id")
