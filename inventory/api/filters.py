import django_filters
from django.db.models import Q
from django.utils import timezone

from inventory.models import StockBalance, StockBatchBalance, StockMovement


class StockBalanceFilter(django_filters.FilterSet):
    product = django_filters.NumberFilter(field_name="product_id")
    location = django_filters.NumberFilter(field_name="location_id")
    min_quantity = django_filters.NumberFilter(field_name="quantity", lookup_expr="gte")

    class Meta:
        model = StockBalance
        fields = ("product", "location", "min_quantity")


class StockBatchBalanceFilter(django_filters.FilterSet):
    product = django_filters.NumberFilter(field_name="batch__product_id")
    location = django_filters.NumberFilter(field_name="location_id")
    min_quantity = django_filters.NumberFilter(field_name="quantity", lookup_expr="gte")
    expiry_before = django_filters.DateFilter(field_name="batch__expiry_date", lookup_expr="lte")
    expiry_after = django_filters.DateFilter(field_name="batch__expiry_date", lookup_expr="gte")
    expired = django_filters.BooleanFilter(method="filter_expired")

    class Meta:
        model = StockBatchBalance
        fields = ("product", "location", "min_quantity", "expiry_before", "expiry_after", "expired")

    def filter_expired(self, queryset, name, value):
        if value is None:
            return queryset
        today = timezone.localdate()
        if value:
            return queryset.filter(batch__expiry_date__lt=today)
        return queryset.filter(Q(batch__expiry_date__isnull=True) | Q(batch__expiry_date__gte=today))


class StockMovementFilter(django_filters.FilterSet):
    movement_type = django_filters.ChoiceFilter(choices=StockMovement.MovementType.choices)
    source_location = django_filters.NumberFilter(field_name="source_location_id")
    destination_location = django_filters.NumberFilter(field_name="destination_location_id")
    created_by = django_filters.NumberFilter(field_name="created_by_id")

    class Meta:
        model = StockMovement
        fields = ("movement_type", "source_location", "destination_location", "created_by")
