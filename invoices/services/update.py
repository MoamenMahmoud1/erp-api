from django.db import transaction

from common.exceptions import InvalidBusinessOperation
from invoices.models import Invoice, InvoiceItem

from .coupon import _calculator, _validate_coupon
from .lifecycle import load_invoice_for_update


@transaction.atomic
def update_invoice(*, invoice_id, validated_data, actor=None):
    invoice = load_invoice_for_update(invoice_id, actor)
    if invoice.status != Invoice.Status.DRAFT:
        raise InvalidBusinessOperation("Only draft invoices can be edited.")

    data = validated_data.copy()
    items = data.pop("items", None)
    if items is not None:
        if not items:
            raise InvalidBusinessOperation("An invoice must contain at least one item.")
        product_ids = [item["product"].pk for item in items]
        if len(product_ids) != len(set(product_ids)):
            raise InvalidBusinessOperation("A product cannot appear more than once in an invoice.")
        if any(not item["product"].is_active for item in items):
            raise InvalidBusinessOperation("Inactive products cannot be added to an invoice.")
        invoice.items.all().delete()
        InvoiceItem.objects.bulk_create(
            [InvoiceItem(invoice=invoice, product=item["product"], quantity=item["quantity"], unit_price=item["product"].selling_price) for item in items]
        )

    for field, value in data.items():
        setattr(invoice, field, value)

    if invoice.coupon_id:
        _validate_coupon(invoice.coupon, invoice)
        invoice.coupon_discount = _calculator.coupon_discount_value(invoice.coupon, _calculator.subtotal(invoice))

    invoice.save(update_fields=("customer", "coupon_discount", "updated_at"))
    return invoice


class UpdateInvoice:
    def __call__(self, *, invoice_id, validated_data, actor=None):
        return update_invoice(invoice_id=invoice_id, validated_data=validated_data, actor=actor)
