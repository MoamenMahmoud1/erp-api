from decimal import Decimal

from rest_framework import serializers

from accounts.models import RoleProfile
from invoices.models import Invoice, InvoiceItem, InvoiceReturn, InvoiceReturnItem


class InvoiceItemSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source="product.name", read_only=True)
    line_total = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    gross_profit = serializers.SerializerMethodField()
    returned_quantity = serializers.SerializerMethodField()

    class Meta:
        model = InvoiceItem
        fields = (
            "id", "product", "product_name", "quantity", "returned_quantity",
            "unit_price", "line_total", "gross_profit",
        )
        read_only_fields = (
            "id", "product_name", "returned_quantity", "unit_price", "line_total", "gross_profit",
        )

    def get_fields(self):
        fields = super().get_fields()
        request = self.context.get("request")
        user = getattr(request, "user", None)
        if RoleProfile.requires_shift_for_user(user):
            fields.pop("gross_profit", None)
        return fields

    def get_returned_quantity(self, obj):
        return sum(item.quantity for item in obj.return_items.all())

    def get_gross_profit(self, obj):
        if obj.cost_price is None:
            return None
        return (obj.unit_price - obj.cost_price) * obj.quantity


class InvoiceSerializer(serializers.ModelSerializer):
    customer_name = serializers.CharField(source="customer.name", read_only=True)
    site_name = serializers.CharField(source="site.name", read_only=True)
    shift_id = serializers.IntegerField(source="shift.id", read_only=True, allow_null=True)
    created_by_name = serializers.SerializerMethodField()
    created_by_username = serializers.SerializerMethodField()
    salesperson_name = serializers.SerializerMethodField()
    items = InvoiceItemSerializer(many=True)
    subtotal = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    total = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    sold_quantity = serializers.IntegerField(read_only=True)
    paid_amount = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    refunded_amount = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    net_paid_amount = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    returned_amount = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    outstanding_amount = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    gross_profit = serializers.SerializerMethodField()

    class Meta:
        model = Invoice
        fields = (
            "id", "customer", "customer_name", "site", "site_name", "shift_id", "created_by", "created_by_name", "created_by_username", "salesperson_name",
            "coupon", "coupon_discount", "status", "subtotal", "total", "paid_amount", "refunded_amount", "net_paid_amount",
            "returned_amount", "outstanding_amount", "sold_quantity", "gross_profit", "items", "created_at", "updated_at",
        )
        read_only_fields = (
            "id", "created_by", "customer_name", "site_name", "shift_id", "created_by_name", "created_by_username", "salesperson_name", "coupon", "coupon_discount", "status",
            "subtotal", "total", "paid_amount", "refunded_amount", "net_paid_amount", "returned_amount", "outstanding_amount", "sold_quantity",
            "gross_profit", "created_at", "updated_at",
        )

    def get_fields(self):
        fields = super().get_fields()
        request = self.context.get("request")
        user = getattr(request, "user", None)
        if RoleProfile.requires_shift_for_user(user):
            fields.pop("gross_profit", None)
        return fields

    def get_created_by_name(self, obj):
        return obj.created_by.get_full_name() or obj.created_by.username

    def get_created_by_username(self, obj):
        return obj.created_by.username

    def get_salesperson_name(self, obj):
        employee = getattr(obj.created_by, "employee", None)
        return str(employee) if employee is not None else obj.created_by.get_full_name() or obj.created_by.username

    def get_gross_profit(self, obj):
        return sum(((item.unit_price - item.cost_price) * item.quantity for item in obj.items.all() if item.cost_price is not None), Decimal("0"))


class InvoiceSummarySerializer(serializers.ModelSerializer):
    customer_name = serializers.CharField(source="customer.name", read_only=True)
    site_name = serializers.CharField(source="site.name", read_only=True)
    shift_id = serializers.IntegerField(source="shift.id", read_only=True, allow_null=True)
    salesperson_name = serializers.SerializerMethodField()
    created_by_name = serializers.SerializerMethodField()
    subtotal = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    total = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    sold_quantity = serializers.IntegerField(read_only=True)
    paid_amount = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    refunded_amount = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    net_paid_amount = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    returned_amount = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    outstanding_amount = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)

    class Meta:
        model = Invoice
        fields = (
            "id", "customer", "customer_name", "site", "site_name", "shift_id", "created_by", "created_by_name", "salesperson_name", "status", "subtotal", "coupon_discount",
            "total", "paid_amount", "refunded_amount", "net_paid_amount", "returned_amount", "outstanding_amount", "sold_quantity", "created_at", "updated_at",
        )
        read_only_fields = fields

    def get_created_by_name(self, obj):
        return obj.created_by.get_full_name() or obj.created_by.username

    def get_salesperson_name(self, obj):
        employee = getattr(obj.created_by, "employee", None)
        return str(employee) if employee is not None else obj.created_by.get_full_name() or obj.created_by.username


class InvoiceReturnItemInputSerializer(serializers.ModelSerializer):
    class Meta:
        model = InvoiceReturnItem
        fields = ("invoice_item", "quantity", "condition")


class InvoiceReturnInputSerializer(serializers.Serializer):
    reason = serializers.CharField(required=False, allow_blank=True)
    items = InvoiceReturnItemInputSerializer(many=True)


class InvoiceReturnSerializer(serializers.ModelSerializer):
    merchandise_amount = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    total_amount = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    site_name = serializers.CharField(source="site.name", read_only=True)
    shift_id = serializers.IntegerField(source="shift.id", read_only=True, allow_null=True)

    class Meta:
        model = InvoiceReturn
        fields = (
            "id", "invoice", "site", "site_name", "shift_id", "created_by", "reason", "merchandise_amount", "refund_amount",
            "total_amount", "created_at",
        )
        read_only_fields = fields
