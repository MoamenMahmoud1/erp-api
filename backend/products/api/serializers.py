from rest_framework import serializers

from accounts.models import RoleProfile
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
        read_only_fields = (
            "id", "created_at", "updated_at", "total_stock", "stock_quantity", "sold_quantity",
        )

    def get_fields(self):
        fields = super().get_fields()
        request = self.context.get("request")
        user = getattr(request, "user", None)
        if RoleProfile.requires_shift_for_user(user):
            fields.pop("purchase_price", None)
        return fields


class CartonPricingSerializer(serializers.ModelSerializer):
    product = serializers.PrimaryKeyRelatedField(queryset=Product.objects.active())
    product_name = serializers.CharField(source="product.name", read_only=True)

    class Meta:
        model = CartonPricing
        fields = (
            "id", "product", "product_name", "name", "units_per_carton", "carton_price",
            "created_at", "updated_at",
        )
        read_only_fields = ("id", "product_name", "created_at", "updated_at")
