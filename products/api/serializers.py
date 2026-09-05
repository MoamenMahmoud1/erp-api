from rest_framework import serializers

from products.models import CartonPricing, Product


class ProductSerializer(serializers.ModelSerializer):
    sold_quantity = serializers.IntegerField(read_only=True)
    total_stock = serializers.IntegerField(read_only=True)
    stock_quantity = serializers.IntegerField(read_only=True, source="total_stock")

    class Meta:
        model = Product
        fields = (
            "id", "name", "category", "purchase_price", "selling_price", "is_active",
            "total_stock", "stock_quantity", "sold_quantity", "created_at", "updated_at",
        )
        read_only_fields = ("id", "created_at", "updated_at", "total_stock", "stock_quantity", "sold_quantity")


class CartonPricingSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source="product.name", read_only=True)

    class Meta:
        model = CartonPricing
        fields = (
            "id", "product", "product_name", "name", "units_per_carton", "carton_price",
            "created_at", "updated_at",
        )
        read_only_fields = ("id", "product_name", "created_at", "updated_at")
