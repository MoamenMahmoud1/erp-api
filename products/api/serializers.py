from asgiref.sync import sync_to_async
from adrf import serializers

from products.models import CartonPricing, Product


class ProductSerializer(serializers.ModelSerializer):
    sold_quantity = serializers.IntegerField(read_only=True)
    total_stock = serializers.IntegerField(read_only=True)

    stock_quantity = serializers.IntegerField(
        read_only=True,
        source="total_stock",
        help_text=(
            "DEPRECATED derived alias of total_stock. Computed from "
            "inventory.StockBalance — NOT an independently stored value."
        ),
    )

    class Meta:
        model = Product
        fields = (
            "id",
            "name",
            "category",
            "purchase_price",
            "selling_price",
            "total_stock",
            "stock_quantity",
            "sold_quantity",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "id",
            "created_at",
            "updated_at",
            "total_stock",
            "stock_quantity",
            "sold_quantity",
        )

    def create(self, validated_data):
        return Product.objects.create(**validated_data)

    async def acreate(self, validated_data):
        return await sync_to_async(
            self.create,
            thread_sensitive=True,
        )(validated_data)

    def update(self, instance, validated_data):
        for attribute, value in validated_data.items():
            setattr(instance, attribute, value)
        instance.save()
        return instance

    async def aupdate(self, instance, validated_data):
        return await sync_to_async(
            self.update,
            thread_sensitive=True,
        )(instance, validated_data)


class CartonPricingSerializer(serializers.ModelSerializer):
    class Meta:
        model = CartonPricing
        fields = (
            "id",
            "name",
            "units_per_carton",
            "carton_price",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "id",
            "created_at",
            "updated_at",
        )

    def create(self, validated_data):
        return CartonPricing.objects.create(**validated_data)

    async def acreate(self, validated_data):
        return await sync_to_async(
            self.create,
            thread_sensitive=True,
        )(validated_data)

    def update(self, instance, validated_data):
        for attribute, value in validated_data.items():
            setattr(instance, attribute, value)
        instance.save()
        return instance

    async def aupdate(self, instance, validated_data):
        return await sync_to_async(
            self.update,
            thread_sensitive=True,
        )(instance, validated_data)
