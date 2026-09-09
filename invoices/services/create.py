from django.db import transaction

from common.exceptions import InvalidBusinessOperation
from common.money import quantize_money
from invoices.models import Invoice, InvoiceItem


def _validate_items(items):
    if not items:
        raise InvalidBusinessOperation("An invoice must contain at least one item.")
    product_ids = [item["product"].pk for item in items]
    if len(product_ids) != len(set(product_ids)):
        raise InvalidBusinessOperation("A product cannot appear more than once.")
    if any(not item["product"].is_active for item in items):
        raise InvalidBusinessOperation("Inactive products cannot be added to an invoice.")


def _resolve_site(*, created_by_id, site):
    from accounts.models import Employee
    from organization.models import Site

    employee = Employee.objects.select_related("work_site").filter(user_id=created_by_id).first()
    if site is None and employee and employee.work_site_id:
        site = employee.work_site
    if site is None:
        return None
    if not site.is_active:
        raise InvalidBusinessOperation("The selected branch/store is inactive.")
    if employee and employee.work_site_id and employee.work_site.company_id != site.company_id:
        raise InvalidBusinessOperation("The invoice site must belong to the employee's company.")
    if employee and employee.work_site_id and employee.work_site.site_type != "head_office":
        allowed = site.pk == employee.work_site_id or site.parent_id == employee.work_site_id
        if not allowed:
            raise InvalidBusinessOperation("The invoice site is outside the employee's branch scope.")
    return Site.objects.get(pk=site.pk)


def _create_invoice(*, created_by_id, validated_data):
    invoice_data = validated_data.copy()
    items = invoice_data.pop("items")
    _validate_items(items)
    invoice_data["site"] = _resolve_site(created_by_id=created_by_id, site=invoice_data.get("site"))

    with transaction.atomic():
        invoice = Invoice.objects.create(created_by_id=created_by_id, **invoice_data)
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
