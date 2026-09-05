from rest_framework import serializers

from invoices.models import Invoice, InvoiceItem, InvoiceReturn, InvoiceReturnItem


class InvoiceItemSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source="product.name", read_only=True)
    line_total = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)

    class Meta:
        model = InvoiceItem
        fields = ("id", "product", "product_name", "quantity", "unit_price", "line_total")
        read_only_fields = ("id", "product_name", "unit_price", "line_total")


class InvoiceSerializer(serializers.ModelSerializer):
    items = InvoiceItemSerializer(many=True)
    subtotal = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    total = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    sold_quantity = serializers.IntegerField(read_only=True)
    paid_amount = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    outstanding_amount = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)

    class Meta:
        model = Invoice
        fields = (
            "id", "customer", "created_by", "coupon", "coupon_discount", "status",
            "subtotal", "total", "paid_amount", "outstanding_amount", "sold_quantity",
            "items", "created_at", "updated_at",
        )
        read_only_fields = (
            "id", "created_by", "coupon", "coupon_discount", "status", "subtotal",
            "total", "paid_amount", "outstanding_amount", "sold_quantity", "created_at",
            "updated_at",
        )


class InvoiceSummarySerializer(serializers.ModelSerializer):
    customer_name = serializers.CharField(source="customer.name", read_only=True)
    subtotal = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    total = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    sold_quantity = serializers.IntegerField(read_only=True)
    paid_amount = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    outstanding_amount = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)

    class Meta:
        model = Invoice
        fields = (
            "id", "customer", "customer_name", "status", "subtotal", "coupon_discount",
            "total", "paid_amount", "outstanding_amount", "sold_quantity", "created_at",
            "updated_at",
        )


class InvoiceReturnItemInputSerializer(serializers.ModelSerializer):
    class Meta:
        model = InvoiceReturnItem
        fields = ("invoice_item", "quantity", "condition")


class InvoiceReturnInputSerializer(serializers.Serializer):
    reason = serializers.CharField(required=False, allow_blank=True)
    items = InvoiceReturnItemInputSerializer(many=True)


class InvoiceReturnSerializer(serializers.ModelSerializer):
    total_amount = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)

    class Meta:
        model = InvoiceReturn
        fields = ("id", "invoice", "created_by", "reason", "total_amount", "created_at")
        read_only_fields = fields
