from django.db import transaction

from common.exceptions import InvalidBusinessOperation
from common.money import quantize_money
from invoices.models import Invoice, InvoiceItem
from accounts.services.employee_shift import employee_for_user, require_open_shift


def _validate_items(items):
    if not items:
        raise InvalidBusinessOperation("An invoice must contain at least one item.")
    product_ids = [item["product"].pk for item in items]
    if len(product_ids) != len(set(product_ids)):
        raise InvalidBusinessOperation("A product cannot appear more than once.")
    if any(not item["product"].is_active for item in items):
        raise InvalidBusinessOperation("Inactive products cannot be added to an invoice.")


@transaction.atomic
def _create_invoice(*, created_by_id, validated_data):
    invoice_data = validated_data.copy()
    items = invoice_data.pop("items")
    invoice_data.pop("site", None)
    invoice_data.pop("shift", None)
    _validate_items(items)

    from django.contrib.auth import get_user_model

    user = get_user_model().objects.get(pk=created_by_id)
    employee = employee_for_user(user)
    shift = require_open_shift(user)
    site_id = shift.site_id if shift else employee.work_site_id
    if site_id is None:
        raise InvalidBusinessOperation("The employee must be assigned to a site before creating an invoice.")

    invoice = Invoice.objects.create(
        created_by_id=created_by_id,
        site_id=site_id,
        shift_id=shift.pk if shift else None,
        **invoice_data,
    )
    InvoiceItem.objects.bulk_create(
        [
            InvoiceItem(
                invoice=invoice,
                product=item["product"],
                quantity=item["quantity"],
                unit_price=quantize_money(item["product"].selling_price),
            )
            for item in items
        ]
    )
    return invoice


class CreateInvoice:
    def __call__(self, *, created_by_id, validated_data):
        return _create_invoice(created_by_id=created_by_id, validated_data=validated_data)
