from django.db import transaction

from common.exceptions import InvalidBusinessOperation
from purchases.models import Purchase, PurchaseItem


def _validate_items(items):
    if not items:
        raise InvalidBusinessOperation("Purchase must contain at least one item.")
    product_ids = [item["product"].pk for item in items]
    if len(product_ids) != len(set(product_ids)):
        raise InvalidBusinessOperation("A product cannot appear more than once.")
    if any(not item["product"].is_active for item in items):
        raise InvalidBusinessOperation("Inactive products cannot be added to a purchase.")


@transaction.atomic
def create_purchase(*, created_by, validated_data):
    data = validated_data.copy()
    items = data.pop("items")
    _validate_items(items)
    supplier = data["supplier"]
    if not supplier.is_active:
        raise InvalidBusinessOperation("Supplier is inactive.")
    purchase = Purchase.objects.create(created_by=created_by, **data)
    PurchaseItem.objects.bulk_create([PurchaseItem(purchase=purchase, **item) for item in items])
    return purchase


@transaction.atomic
def update_purchase(*, purchase_id, validated_data):
    purchase = Purchase.objects.select_for_update().get(pk=purchase_id)
    if purchase.status != Purchase.Status.DRAFT:
        raise InvalidBusinessOperation("Only draft purchases can be edited.")
    data = validated_data.copy()
    items = data.pop("items", None)
    if "supplier" in data and not data["supplier"].is_active:
        raise InvalidBusinessOperation("Supplier is inactive.")
    if items is not None:
        _validate_items(items)
        purchase.items.all().delete()
        PurchaseItem.objects.bulk_create([PurchaseItem(purchase=purchase, **item) for item in items])
    for field, value in data.items():
        setattr(purchase, field, value)
    purchase.save()
    return purchase


@transaction.atomic
def delete_purchase(*, purchase_id):
    purchase = Purchase.objects.select_for_update().get(pk=purchase_id)
    if purchase.status != Purchase.Status.DRAFT:
        raise InvalidBusinessOperation("Only draft purchases can be deleted.")
    purchase.delete()


class CreatePurchase:
    def __call__(self, *, created_by, validated_data):
        return create_purchase(created_by=created_by, validated_data=validated_data)


class UpdatePurchase:
    def __call__(self, *, purchase_id, validated_data):
        return update_purchase(purchase_id=purchase_id, validated_data=validated_data)


class DeletePurchase:
    def __call__(self, *, purchase_id):
        return delete_purchase(purchase_id=purchase_id)
