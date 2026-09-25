import django_filters
from django.db.models import Q

from invoices.models import Invoice


class InvoiceFilter(django_filters.FilterSet):
    customer = django_filters.NumberFilter(field_name="customer_id")
    status = django_filters.ChoiceFilter(choices=Invoice.Status.choices)
    created_by = django_filters.NumberFilter(field_name="created_by_id")
    site = django_filters.NumberFilter(field_name="site_id")
    created_date_from = django_filters.DateFilter(field_name="created_at", lookup_expr="date__gte")
    created_date_to = django_filters.DateFilter(field_name="created_at", lookup_expr="date__lte")
    created_by_name = django_filters.CharFilter(method="filter_created_by_name")

    class Meta:
        model = Invoice
        fields = ("customer", "status", "created_by", "site", "created_date_from", "created_date_to", "created_by_name")

    def filter_created_by_name(self, queryset, name, value):
        value = value.strip()
        if not value:
            return queryset
        return queryset.filter(
            Q(created_by__username__icontains=value)
            | Q(created_by__email__icontains=value)
            | Q(created_by__first_name__icontains=value)
            | Q(created_by__last_name__icontains=value)
        )
