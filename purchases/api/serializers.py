from django.db import transaction
from rest_framework import serializers

from purchases.models import Purchase, PurchaseItem


class PurchaseItemSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source="product.name", read_only=True)

    class Meta:
        model = PurchaseItem
        fields = (
            "id",
            "product",
            "product_name",
            "quantity",
            "unit_purchase_price",
            "total_amount",
        )
        read_only_fields = ("id", "product_name", "total_amount")


class PurchaseListSerializer(serializers.ModelSerializer):
    supplier_name = serializers.CharField(source="supplier.name", read_only=True)
    total_amount = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)

    class Meta:
        model = Purchase
        fields = (
            "id",
            "supplier",
            "supplier_name",
            "status",
            "reference",
            "created_at",
            "total_amount",
        )
        read_only_fields = fields


class PurchaseSerializer(serializers.ModelSerializer):
    items = PurchaseItemSerializer(many=True)
    supplier_name = serializers.CharField(source="supplier.name", read_only=True)
    total_amount = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)

    class Meta:
        model = Purchase
        fields = (
            "id",
            "supplier",
            "supplier_name",
            "status",
            "reference",
            "created_by",
            "created_at",
            "updated_at",
            "total_amount",
            "items",
        )
        read_only_fields = (
            "id",
            "status",
            "created_by",
            "created_at",
            "updated_at",
            "total_amount",
        )

    def validate_supplier(self, supplier):
        if not supplier.is_active:
            raise serializers.ValidationError("Supplier is inactive.")
        return supplier

    def validate_items(self, items):
        if not items:
            raise serializers.ValidationError("Purchase must contain at least one item.")
        product_ids = [item["product"].pk for item in items]
        if len(product_ids) != len(set(product_ids)):
            raise serializers.ValidationError("A product cannot appear more than once.")
        return items

    def create(self, validated_data):
        user = self.context["request"].user
        items_data = validated_data.pop("items")
        with transaction.atomic():
            purchase = Purchase.objects.create(created_by=user, **validated_data)
            PurchaseItem.objects.bulk_create(
                [PurchaseItem(purchase=purchase, **item_data) for item_data in items_data]
            )
        return purchase

    def update(self, instance, validated_data):
        if instance.status != Purchase.Status.DRAFT:
            raise serializers.ValidationError("Only draft purchases can be edited.")

        items_data = validated_data.pop("items", None)
        with transaction.atomic():
            for attr, value in validated_data.items():
                setattr(instance, attr, value)
            instance.save()

            if items_data is not None:
                instance.items.all().delete()
                PurchaseItem.objects.bulk_create(
                    [
                        PurchaseItem(purchase=instance, **item_data)
                        for item_data in items_data
                    ]
                )
        return instance
