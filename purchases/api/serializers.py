from asgiref.sync import sync_to_async
from django.db import transaction
from adrf import serializers

from purchases.models import Purchase, PurchaseItem


class PurchaseItemSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(
        source="product.name",
        read_only=True,
    )

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
        read_only_fields = (
            "id",
            "product_name",
            "total_amount",
        )


class PurchaseListSerializer(serializers.ModelSerializer):
    supplier_name = serializers.CharField(
        source="supplier.name",
        read_only=True,
    )
    total_amount = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
        read_only=True,
    )

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
        read_only_fields = (
            "id",
            "supplier",
            "supplier_name",
            "status",
            "reference",
            "created_at",
            "total_amount",
        )


class PurchaseSerializer(serializers.ModelSerializer):
    items = PurchaseItemSerializer(many=True)

    supplier_name = serializers.CharField(
        source="supplier.name",
        read_only=True,
    )
    total_amount = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
        read_only=True,
    )

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
            raise serializers.ValidationError(
                "Supplier is inactive."
            )

        return supplier

    def validate_items(self, items):
        if not items:
            raise serializers.ValidationError(
                "Purchase must contain at least one item."
            )

        product_ids = [item["product"].pk for item in items]

        if len(product_ids) != len(set(product_ids)):
            raise serializers.ValidationError(
                "A product cannot appear more than once."
            )

        return items

    @staticmethod
    @transaction.atomic
    def _create_sync(validated_data, user):
        items_data = validated_data.pop("items")

        purchase = Purchase.objects.create(
            created_by=user,
            **validated_data,
        )

        PurchaseItem.objects.bulk_create(
            [
                PurchaseItem(
                    purchase=purchase,
                    **item_data,
                )
                for item_data in items_data
            ]
        )

        return purchase

    async def acreate(self, validated_data):
        user = self.context["request"].user

        return await sync_to_async(
            self._create_sync,
            thread_sensitive=True,
        )(
            validated_data,
            user,
        )

    @staticmethod
    @transaction.atomic
    def _update_sync(instance, validated_data):
        if instance.status != Purchase.Status.DRAFT:
            raise serializers.ValidationError(
                "Only draft purchases can be edited."
            )

        items_data = validated_data.pop("items", None)

        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        instance.save()

        if items_data is not None:
            instance.items.all().delete()

            PurchaseItem.objects.bulk_create(
                [
                    PurchaseItem(
                        purchase=instance,
                        **item_data,
                    )
                    for item_data in items_data
                ]
            )

        return instance

    async def aupdate(self, instance, validated_data):
        return await sync_to_async(
            self._update_sync,
            thread_sensitive=True,
        )(
            instance,
            validated_data,
        )