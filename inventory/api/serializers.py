from rest_framework import serializers

from inventory.models import StockBalance, StockLocation, StockMovement, StockMovementItem


class StockLocationSerializer(serializers.ModelSerializer):
    class Meta:
        model = StockLocation
        fields = ("id", "name", "location_type", "employee", "is_active", "created_at")
        read_only_fields = fields


class StockBalanceSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source="product.name", read_only=True)
    location_name = serializers.CharField(source="location.name", read_only=True)

    class Meta:
        model = StockBalance
        fields = ("id", "product", "product_name", "location", "location_name", "quantity", "updated_at")
        read_only_fields = fields


class StockMovementItemSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source="product.name", read_only=True)

    class Meta:
        model = StockMovementItem
        fields = ("id", "product", "product_name", "quantity")
        read_only_fields = fields


class StockMovementSerializer(serializers.ModelSerializer):
    items = StockMovementItemSerializer(many=True, read_only=True)

    class Meta:
        model = StockMovement
        fields = (
            "id", "movement_type", "source_location", "destination_location",
            "created_by", "created_at", "reference", "items",
        )
        read_only_fields = fields


class TransferItemInputSerializer(serializers.Serializer):
    product = serializers.IntegerField(min_value=1)
    quantity = serializers.IntegerField(min_value=1)


class TransferInputSerializer(serializers.Serializer):
    source_location = serializers.IntegerField(min_value=1)
    destination_location = serializers.IntegerField(min_value=1)
    reference = serializers.CharField(required=False, allow_blank=True)
    items = TransferItemInputSerializer(many=True)
