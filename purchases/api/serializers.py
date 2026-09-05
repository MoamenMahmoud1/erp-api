from rest_framework import serializers

from purchases.models import Purchase, PurchaseItem, PurchaseReturn, PurchaseReturnItem


class PurchaseItemSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source="product.name", read_only=True)

    class Meta:
        model = PurchaseItem
        fields = ("id", "product", "product_name", "quantity", "unit_purchase_price", "total_amount")
        read_only_fields = ("id", "product_name", "total_amount")


class PurchaseListSerializer(serializers.ModelSerializer):
    supplier_name = serializers.CharField(source="supplier.name", read_only=True)
    total_amount = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)

    class Meta:
        model = Purchase
        fields = ("id", "supplier", "supplier_name", "status", "reference", "created_at", "total_amount")
        read_only_fields = fields


class PurchaseSerializer(serializers.ModelSerializer):
    items = PurchaseItemSerializer(many=True)
    supplier_name = serializers.CharField(source="supplier.name", read_only=True)
    total_amount = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)

    class Meta:
        model = Purchase
        fields = (
            "id", "supplier", "supplier_name", "status", "reference", "created_by",
            "created_at", "updated_at", "total_amount", "items",
        )
        read_only_fields = (
            "id", "status", "created_by", "created_at", "updated_at", "total_amount",
        )


class PurchaseReturnItemInputSerializer(serializers.ModelSerializer):
    class Meta:
        model = PurchaseReturnItem
        fields = ("purchase_item", "quantity")


class PurchaseReturnInputSerializer(serializers.Serializer):
    reason = serializers.CharField(required=False, allow_blank=True)
    items = PurchaseReturnItemInputSerializer(many=True)


class PurchaseReturnSerializer(serializers.ModelSerializer):
    total_amount = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)

    class Meta:
        model = PurchaseReturn
        fields = ("id", "purchase", "created_by", "reason", "total_amount", "created_at")
        read_only_fields = fields
