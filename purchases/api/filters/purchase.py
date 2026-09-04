import django_filters

from purchases.models import Purchase


class PurchaseFilter(django_filters.FilterSet):
    status = django_filters.CharFilter(
        field_name="status",
    )

    supplier = django_filters.NumberFilter(
        field_name="supplier_id",
    )

    created_at_after = django_filters.IsoDateTimeFilter(
        field_name="created_at",
        lookup_expr="gte",
    )

    created_at_before = django_filters.IsoDateTimeFilter(
        field_name="created_at",
        lookup_expr="lte",
    )

    class Meta:
        model = Purchase
        fields = (
            "status",
            "supplier",
            "created_at_after",
            "created_at_before",
        )