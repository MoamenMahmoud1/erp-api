from rest_framework import serializers

from inventory.models import InventoryBatch, StockBalance, StockBatchBalance, StockLocation, StockMovement, StockMovementItem
from products.models import Product


class StockLocationSerializer(serializers.ModelSerializer):
    employee_name = serializers.SerializerMethodField()
    site_name = serializers.CharField(source="site.name", read_only=True, allow_null=True)

    class Meta:
        model = StockLocation
        fields = ("id", "site", "site_name", "name", "location_type", "employee", "employee_name", "is_active", "created_at")
        read_only_fields = fields

    def get_employee_name(self, obj):
        if not obj.employee_id:
            return None
        return obj.employee.get_full_name() or obj.employee.username


class InventoryBatchSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source="product.name", read_only=True)

    class Meta:
        model = InventoryBatch
        fields = ("id", "product", "product_name", "batch_number", "manufactured_date", "expiry_date", "created_at", "is_expired", "days_to_expiry")
        read_only_fields = fields

    is_expired = serializers.BooleanField(read_only=True)
    days_to_expiry = serializers.IntegerField(read_only=True, allow_null=True)


class StockBatchBalanceSerializer(serializers.ModelSerializer):
    batch_id = serializers.IntegerField(source="batch.id", read_only=True)
    batch_number = serializers.CharField(source="batch.batch_number", read_only=True, allow_null=True)
    product = serializers.IntegerField(source="batch.product.id", read_only=True)
    product_name = serializers.CharField(source="batch.product.name", read_only=True)
    location_name = serializers.CharField(source="location.name", read_only=True)
    site_name = serializers.CharField(source="location.site.name", read_only=True, allow_null=True)
    manufactured_date = serializers.DateField(source="batch.manufactured_date", read_only=True, allow_null=True)
    expiry_date = serializers.DateField(source="batch.expiry_date", read_only=True, allow_null=True)
    is_expired = serializers.BooleanField(source="batch.is_expired", read_only=True)
    days_to_expiry = serializers.IntegerField(source="batch.days_to_expiry", read_only=True, allow_null=True)
    average_unit_cost = serializers.DecimalField(max_digits=14, decimal_places=2, read_only=True)

    class Meta:
        model = StockBatchBalance
        fields = (
            "id", "batch_id", "batch_number", "product", "product_name", "location", "location_name", "site_name",
            "manufactured_date", "expiry_date", "is_expired", "days_to_expiry", "quantity", "total_cost", "average_unit_cost", "updated_at",
        )
        read_only_fields = fields


class StockBalanceSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source="product.name", read_only=True)
    location_name = serializers.CharField(source="location.name", read_only=True)
    site_name = serializers.CharField(source="location.site.name", read_only=True, allow_null=True)
    average_unit_cost = serializers.DecimalField(max_digits=14, decimal_places=2, read_only=True)

    class Meta:
        model = StockBalance
        fields = ("id", "product", "product_name", "location", "location_name", "site_name", "quantity", "total_cost", "average_unit_cost", "updated_at")
        read_only_fields = fields


class StockMovementItemSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source="product.name", read_only=True)
    batch_number = serializers.CharField(source="batch.batch_number", read_only=True, allow_null=True)
    expiry_date = serializers.DateField(source="batch.expiry_date", read_only=True, allow_null=True)
    total_cost = serializers.DecimalField(max_digits=16, decimal_places=2, read_only=True)

    class Meta:
        model = StockMovementItem
        fields = ("id", "product", "product_name", "batch", "batch_number", "expiry_date", "quantity", "unit_cost", "total_cost")
        read_only_fields = fields


class StockMovementSerializer(serializers.ModelSerializer):
    source_location_name = serializers.CharField(source="source_location.name", read_only=True, allow_null=True)
    destination_location_name = serializers.CharField(source="destination_location.name", read_only=True, allow_null=True)
    source_site_name = serializers.CharField(source="source_location.site.name", read_only=True, allow_null=True)
    destination_site_name = serializers.CharField(source="destination_location.site.name", read_only=True, allow_null=True)
    shift_id = serializers.IntegerField(source="shift.id", read_only=True, allow_null=True)
    created_by_name = serializers.SerializerMethodField()
    items = StockMovementItemSerializer(many=True, read_only=True)

    class Meta:
        model = StockMovement
        fields = (
            "id", "movement_type", "shift_id", "source_location", "source_location_name", "source_site_name",
            "destination_location", "destination_location_name", "destination_site_name", "created_by", "created_by_name",
            "created_at", "reference", "items",
        )
        read_only_fields = fields

    def get_created_by_name(self, obj):
        return obj.created_by.get_full_name() or obj.created_by.username


class TransferItemInputSerializer(serializers.Serializer):
    product = serializers.PrimaryKeyRelatedField(queryset=Product.objects.active())
    quantity = serializers.IntegerField(min_value=1)


class TransferInputSerializer(serializers.Serializer):
    source_location = serializers.IntegerField(min_value=1)
    destination_location = serializers.IntegerField(min_value=1)
    reference = serializers.CharField(required=False, allow_blank=True)
    items = TransferItemInputSerializer(many=True)

    def validate_items(self, value):
        if not value:
            raise serializers.ValidationError("Transfer must contain at least one item.")
        product_ids = [item["product"].pk for item in value]
        if len(product_ids) != len(set(product_ids)):
            raise serializers.ValidationError("A product can appear only once in a transfer.")
        return value
