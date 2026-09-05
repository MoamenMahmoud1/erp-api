import django_filters

from inventory.models import StockMovement


class StockBalanceFilter(django_filters.FilterSet):
    product = django_filters.NumberFilter(field_name="product_id")
    location = django_filters.NumberFilter(field_name="location_id")
    min_quantity = django_filters.NumberFilter(field_name="quantity", lookup_expr="gte")

    class Meta:
        from inventory.models import StockBalance
        model = StockBalance
        fields = ("product", "location", "min_quantity")


class StockMovementFilter(django_filters.FilterSet):
    movement_type = django_filters.ChoiceFilter(choices=StockMovement.MovementType.choices)
    source_location = django_filters.NumberFilter(field_name="source_location_id")
    destination_location = django_filters.NumberFilter(field_name="destination_location_id")
    created_by = django_filters.NumberFilter(field_name="created_by_id")

    class Meta:
        model = StockMovement
        fields = ("movement_type", "source_location", "destination_location", "created_by")
