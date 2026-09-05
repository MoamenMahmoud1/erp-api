from django.db import IntegrityError, transaction
from django.db.models import F

from inventory.models import StockBalance


class StockBalanceService:
    @staticmethod
    @transaction.atomic
    def increase(*, location, product, quantity):
        if quantity <= 0:
            raise ValueError("Quantity must be greater than zero.")

        updated = (
            StockBalance.objects
            .filter(location=location, product=product)
            .update(quantity=F("quantity") + quantity)
        )

        if updated == 0:
            try:
                with transaction.atomic():
                    StockBalance.objects.create(
                        location=location,
                        product=product,
                        quantity=quantity,
                    )
            except IntegrityError:
                StockBalance.objects.filter(
                    location=location,
                    product=product,
                ).update(quantity=F("quantity") + quantity)

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

        balance.quantity -= quantity
        balance.save(update_fields=["quantity", "updated_at"])
        return balance
