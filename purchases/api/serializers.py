from rest_framework import serializers

from purchases.models import (
    Purchase,
    PurchaseItem,
    PurchaseReturn,
    PurchaseReturnItem,
    SupplierPayment,
    SupplierPaymentAllocation,
)


class PurchaseItemSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source="product.name", read_only=True)

    class Meta:
        model = PurchaseItem
        fields = ("id", "product", "product_name", "quantity", "unit_purchase_price", "total_amount")
        read_only_fields = ("id", "product_name", "total_amount")


class PurchaseListSerializer(serializers.ModelSerializer):
    supplier_name = serializers.CharField(source="supplier.name", read_only=True)
    site_name = serializers.CharField(source="site.name", read_only=True)
    total_amount = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)

    class Meta:
        model = Purchase
        fields = ("id", "supplier", "supplier_name", "site", "site_name", "status", "reference", "created_at", "total_amount")
        read_only_fields = fields


class PurchaseSerializer(serializers.ModelSerializer):
    items = PurchaseItemSerializer(many=True)
    supplier_name = serializers.CharField(source="supplier.name", read_only=True)
    site_name = serializers.CharField(source="site.name", read_only=True)
    total_amount = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)

    class Meta:
        model = Purchase
        fields = (
            "id", "supplier", "supplier_name", "site", "site_name", "status", "reference", "created_by",
            "created_at", "updated_at", "total_amount", "items",
        )
        read_only_fields = (
            "id", "site_name", "status", "created_by", "created_at", "updated_at", "total_amount",
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
    site_name = serializers.CharField(source="purchase.site.name", read_only=True)

    class Meta:
        model = PurchaseReturn
        fields = ("id", "purchase", "site_name", "created_by", "reason", "total_amount", "created_at")
        read_only_fields = fields


class SupplierPaymentAllocationSerializer(serializers.ModelSerializer):
    total_amount = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    site_name = serializers.CharField(source="purchase.site.name", read_only=True)

    class Meta:
        model = SupplierPaymentAllocation
        fields = ("id", "purchase", "site_name", "cash_amount", "transfer_amount", "total_amount", "created_at")
        read_only_fields = fields


class SupplierPaymentSerializer(serializers.ModelSerializer):
    total_amount = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    allocations = SupplierPaymentAllocationSerializer(many=True, read_only=True)

    class Meta:
        model = SupplierPayment
        fields = (
            "id", "supplier", "paid_by", "cash_amount", "transfer_amount",
            "reference", "total_amount", "created_at", "allocations",
        )
        read_only_fields = ("id", "paid_by", "total_amount", "created_at", "allocations")
