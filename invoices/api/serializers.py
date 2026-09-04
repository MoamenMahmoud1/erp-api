from rest_framework import serializers

from invoices.models import Invoice, InvoiceItem


class InvoiceItemSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(
        source="product.name",
        read_only=True,
    )

    line_total = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
        read_only=True,
    )

    class Meta:
        model = InvoiceItem
        fields = (
            "id",
            "product",
            "product_name",
            "quantity",
            "unit_price",
            "line_total",
        )
        read_only_fields = (
            "id",
            "product_name",
            "unit_price",
            "line_total",
        )

    def validate_quantity(self, value):
        if value < 1:
            raise serializers.ValidationError(
                "Quantity must be at least 1."
            )

        return value


class InvoiceSerializer(serializers.ModelSerializer):
    items = InvoiceItemSerializer(many=True)

    subtotal = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
        read_only=True,
    )

    total = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
        read_only=True,
    )

    sold_quantity = serializers.IntegerField(
        read_only=True,
    )

    paid_amount = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
        read_only=True,
    )

    outstanding_amount = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
        read_only=True,
    )

    class Meta:
        model = Invoice
        fields = (
            "id",
            "customer",
            "created_by",
            "coupon",
            "coupon_discount",
            "status",
            "subtotal",
            "total",
            "paid_amount",
            "outstanding_amount",
            "sold_quantity",
            "items",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "id",
            "created_by",
            "coupon_discount",
            "status",
            "subtotal",
            "total",
            "paid_amount",
            "outstanding_amount",
            "sold_quantity",
            "created_at",
            "updated_at",
        )

    def validate_items(self, items):
        if not items:
            raise serializers.ValidationError(
                "An invoice must contain at least one item."
            )

        product_ids = [item["product"].pk for item in items]
        if len(product_ids) != len(set(product_ids)):
            raise serializers.ValidationError(
                "A product cannot appear more than once."
            )

        return items
class InvoiceSummarySerializer(serializers.ModelSerializer):
    customer_name = serializers.CharField(
        source="customer.name",
        read_only=True,
    )

    subtotal = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
        read_only=True,
    )

    total = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
        read_only=True,
    )

    sold_quantity = serializers.IntegerField(
        read_only=True,
    )

    paid_amount = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
        read_only=True,
    )

    outstanding_amount = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
        read_only=True,
    )

    class Meta:
        model = Invoice

        fields = (
            "id",
            "customer",
            "customer_name",
            "status",
            "subtotal",
            "coupon_discount",
            "total",
            "paid_amount",
            "outstanding_amount",
            "sold_quantity",
            "created_at",
            "updated_at",
        )
