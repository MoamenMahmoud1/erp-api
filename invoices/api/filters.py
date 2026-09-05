import django_filters

from invoices.models import Invoice


class InvoiceFilter(django_filters.FilterSet):
    customer = django_filters.NumberFilter(field_name="customer_id")
    status = django_filters.ChoiceFilter(choices=Invoice.Status.choices)
    created_by = django_filters.NumberFilter(field_name="created_by_id")

    class Meta:
        model = Invoice
        fields = ("customer", "status", "created_by")
