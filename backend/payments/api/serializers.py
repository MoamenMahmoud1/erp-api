from decimal import Decimal

from rest_framework import serializers

from customers.models import Customer
from payments.models import PaymentAllocation, PaymentRefund, PaymentTransaction


class CollectionSerializer(serializers.Serializer):
    customer = serializers.PrimaryKeyRelatedField(queryset=Customer.objects.all())
    invoice = serializers.IntegerField(min_value=1, required=False, allow_null=True)
    cash_amount = serializers.DecimalField(max_digits=12, decimal_places=2, min_value=Decimal("0"), default=Decimal("0"))
    transfer_amount = serializers.DecimalField(max_digits=12, decimal_places=2, min_value=Decimal("0"), default=Decimal("0"))


class RefundInputSerializer(serializers.Serializer):
    transaction = serializers.IntegerField(min_value=1)
    invoice = serializers.IntegerField(min_value=1)
    amount = serializers.DecimalField(max_digits=12, decimal_places=2, min_value=Decimal("0.01"))
    reason = serializers.CharField(required=False, allow_blank=True)


class PaymentAllocationSerializer(serializers.ModelSerializer):
    class Meta:
        model = PaymentAllocation
        fields = ("id", "invoice", "cash_amount", "transfer_amount", "total_amount", "created_at")
        read_only_fields = fields


class PaymentRefundSerializer(serializers.ModelSerializer):
    site_name = serializers.CharField(source="site.name", read_only=True, allow_null=True)
    shift_id = serializers.IntegerField(source="shift.id", read_only=True, allow_null=True)

    class Meta:
        model = PaymentRefund
        fields = (
            "id", "transaction", "invoice", "allocation", "site", "site_name", "shift_id", "cash_amount",
            "transfer_amount", "total_amount", "reason", "created_by", "created_at",
        )
        read_only_fields = fields


class PaymentTransactionSerializer(serializers.ModelSerializer):
    customer_name = serializers.CharField(source="customer.name", read_only=True)
    site_name = serializers.CharField(source="site.name", read_only=True, allow_null=True)
    shift_id = serializers.IntegerField(source="shift.id", read_only=True, allow_null=True)
    allocations = PaymentAllocationSerializer(many=True, read_only=True)
    refunds = PaymentRefundSerializer(many=True, read_only=True)

    class Meta:
        model = PaymentTransaction
        fields = (
            "id", "customer", "customer_name", "site", "site_name", "shift_id", "cash_amount", "transfer_amount",
            "total_amount", "refunded_amount", "refundable_amount", "allocations", "refunds", "created_at",
        )
        read_only_fields = fields
