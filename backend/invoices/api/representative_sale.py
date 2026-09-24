from decimal import Decimal

from rest_framework import serializers

from customer_assignments.services import assigned_customer_queryset
from customers.models import Customer
from products.models import Product


class RepresentativeSaleItemSerializer(serializers.Serializer):
    product = serializers.PrimaryKeyRelatedField(queryset=Product.objects.active())
    quantity = serializers.IntegerField(min_value=1)


class RepresentativeSaleSerializer(serializers.Serializer):
    customer = serializers.PrimaryKeyRelatedField(queryset=Customer.objects.all())
    items = RepresentativeSaleItemSerializer(many=True)
    payment_method = serializers.ChoiceField(choices=("cash", "transfer"), default="cash")
    payment_amount = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
        min_value=Decimal("0"),
        default=Decimal("0"),
    )

    def get_fields(self):
        fields = super().get_fields()
        request = self.context.get("request")
        user = getattr(request, "user", None)
        fields["customer"].queryset = assigned_customer_queryset(user)
        return fields

    def validate_items(self, value):
        if not value:
            raise serializers.ValidationError("A sale must contain at least one item.")
        product_ids = [item["product"].pk for item in value]
        if len(product_ids) != len(set(product_ids)):
            raise serializers.ValidationError("A product cannot appear more than once in a sale.")
        return value
