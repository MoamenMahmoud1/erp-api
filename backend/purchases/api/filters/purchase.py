import django_filters

from django.db.models import Q

from purchases.models import Purchase


class PurchaseFilter(django_filters.FilterSet):
    status = django_filters.CharFilter(field_name="status")
    supplier = django_filters.NumberFilter(field_name="supplier_id")
    site = django_filters.NumberFilter(field_name="site_id")
    created_at_after = django_filters.IsoDateTimeFilter(field_name="created_at", lookup_expr="gte")
    created_at_before = django_filters.IsoDateTimeFilter(field_name="created_at", lookup_expr="lte")
    created_date_from = django_filters.DateFilter(field_name="created_at", lookup_expr="date__gte")
    created_date_to = django_filters.DateFilter(field_name="created_at", lookup_expr="date__lte")
    created_by_name = django_filters.CharFilter(method="filter_created_by_name")

    class Meta:
        model = Purchase
        fields = (
            "status",
            "supplier",
            "site",
            "created_at_after",
            "created_at_before",
            "created_date_from",
            "created_date_to",
            "created_by_name",
        )

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
