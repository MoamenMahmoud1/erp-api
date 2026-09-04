"""Atomic invoice creation service."""

from asgiref.sync import sync_to_async
from django.db import transaction

from common.money import quantize_money
from invoices.models import Invoice, InvoiceItem


def _create_invoice_sync(*, created_by_id, validated_data):
    """Create an invoice and all items within one synchronous transaction."""
    invoice_data = validated_data.copy()
    items = invoice_data.pop("items")

    with transaction.atomic():
        invoice = Invoice.objects.create(created_by_id=created_by_id, **invoice_data)
        for item in items:
            product = item["product"]
            InvoiceItem.objects.create(
                invoice=invoice,
                product=product,
                quantity=item["quantity"],
                unit_price=quantize_money(product.selling_price),
            )

    return invoice


class CreateInvoice:
    """Create an invoice with server-authoritative product-price snapshots."""

    async def __call__(self, *, created_by_id, validated_data):
        return await sync_to_async(
            _create_invoice_sync,
            thread_sensitive=True,
        )(created_by_id=created_by_id, validated_data=validated_data)
