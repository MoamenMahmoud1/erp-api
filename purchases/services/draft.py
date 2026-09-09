from django.db import transaction

from accounts.services.employee_shift import employee_for_user, require_open_shift
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


def _resolve_site(*, created_by, site):
    from organization.models import Site

    employee = getattr(created_by, "employee", None)
    if site is None and employee and employee.work_site_id:
        site = employee.work_site
    if site is None:
        return None
    if not site.is_active:
        raise InvalidBusinessOperation("The selected branch/store is inactive.")
    if employee and employee.work_site_id and employee.work_site.company_id != site.company_id:
        raise InvalidBusinessOperation("The purchase site must belong to the employee's company.")
    if employee and employee.work_site_id and employee.work_site.site_type != "head_office":
        allowed = site.pk == employee.work_site_id or site.parent_id == employee.work_site_id
        if not allowed:
            raise InvalidBusinessOperation("The purchase site is outside the employee's branch scope.")
    return Site.objects.get(pk=site.pk)


def _scoped_purchase(purchase_id, actor, *, for_update=True):
    queryset = Purchase.objects.visible_to(actor)
    if for_update:
        queryset = queryset.select_for_update()
    try:
        return queryset.get(pk=purchase_id)
    except Purchase.DoesNotExist as exc:
        raise InvalidBusinessOperation("Purchase not found or not accessible.") from exc


@transaction.atomic
def create_purchase(*, created_by, validated_data):
    data = validated_data.copy()
    items = data.pop("items")
    _validate_items(items)
    if not data["supplier"].is_active:
        raise InvalidBusinessOperation("Supplier is inactive.")

    shift = require_open_shift(created_by)
    employee = employee_for_user(created_by)
    data["site"] = _resolve_site(created_by=created_by, site=data.get("site") or (shift.site if shift else None))
    data.pop("shift", None)
    purchase = Purchase.objects.create(
        created_by_id=created_by.pk,
        shift_id=shift.pk if shift else None,
        **data,
    )
    PurchaseItem.objects.bulk_create([PurchaseItem(purchase=purchase, **item) for item in items])
    return purchase


@transaction.atomic
def update_purchase(*, purchase_id, validated_data, actor):
    purchase = _scoped_purchase(purchase_id, actor)
    if purchase.status != Purchase.Status.DRAFT:
        raise InvalidBusinessOperation("Only draft purchases can be edited.")
    data = validated_data.copy()
    items = data.pop("items", None)
    data.pop("shift", None)
    if "supplier" in data and not data["supplier"].is_active:
        raise InvalidBusinessOperation("Supplier is inactive.")
    if "site" in data:
        data["site"] = _resolve_site(created_by=actor, site=data["site"])
    if items is not None:
        _validate_items(items)
        purchase.items.all().delete()
        PurchaseItem.objects.bulk_create([PurchaseItem(purchase=purchase, **item) for item in items])
    for field, value in data.items():
        setattr(purchase, field, value)
    purchase.save()
    return purchase


@transaction.atomic
def delete_purchase(*, purchase_id, actor):
    purchase = _scoped_purchase(purchase_id, actor)
    if purchase.status != Purchase.Status.DRAFT:
        raise InvalidBusinessOperation("Only draft purchases can be deleted.")
    purchase.delete()


class CreatePurchase:
    def __call__(self, *, created_by, validated_data):
        return create_purchase(created_by=created_by, validated_data=validated_data)


class UpdatePurchase:
    def __call__(self, *, purchase_id, validated_data, actor):
        return update_purchase(purchase_id=purchase_id, validated_data=validated_data, actor=actor)


class DeletePurchase:
    def __call__(self, *, purchase_id, actor):
        return delete_purchase(purchase_id=purchase_id, actor=actor)
