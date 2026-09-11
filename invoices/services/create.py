from django.db import transaction

from accounts.services.employee_shift import operation_context
from common.exceptions import InvalidBusinessOperation
from common.money import quantize_money
from customer_assignments.services import require_customer_assignment
from invoices.models import Invoice, InvoiceItem


def _validate_items(items):
    if not items:
        raise InvalidBusinessOperation("An invoice must contain at least one item.")
    product_ids = [item["product"].pk for item in items]
    if len(product_ids) != len(set(product_ids)):
        raise InvalidBusinessOperation("A product cannot appear more than once.")
    if any(not item["product"].is_active for item in items):
        raise InvalidBusinessOperation("Inactive products cannot be added to an invoice.")


@transaction.atomic
def _create_invoice(*, created_by, validated_data):
    invoice_data = validated_data.copy()
    items = invoice_data.pop("items")
    requested_site = invoice_data.pop("site", None)
    invoice_data.pop("shift", None)
    _validate_items(items)

    customer = invoice_data.get("customer")
    if customer is None:
        raise InvalidBusinessOperation("A customer is required before creating an invoice.")
    require_customer_assignment(customer=customer, user=created_by)

    _employee, site, shift = operation_context(created_by, requested_site=requested_site)
    if site is None:
        raise InvalidBusinessOperation("A site is required before creating an invoice.")

    invoice = Invoice.objects.create(
        created_by_id=created_by.pk,
        site=site,
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
    def __call__(self, *, created_by, validated_data):
        return _create_invoice(created_by=created_by, validated_data=validated_data)
