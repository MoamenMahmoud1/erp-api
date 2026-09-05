from decimal import Decimal

from rest_framework import serializers

from customers.models import Customer
from payments.models import PaymentAllocation, PaymentRefund, PaymentTransaction


class CollectionSerializer(serializers.Serializer):
    customer = serializers.PrimaryKeyRelatedField(queryset=Customer.objects.all())
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
    class Meta:
        model = PaymentRefund
        fields = (
            "id", "transaction", "invoice", "allocation", "cash_amount",
            "transfer_amount", "total_amount", "reason", "created_by", "created_at",
        )
        read_only_fields = fields


class PaymentTransactionSerializer(serializers.ModelSerializer):
    customer_name = serializers.CharField(source="customer.name", read_only=True)
    allocations = PaymentAllocationSerializer(many=True, read_only=True)
    refunds = PaymentRefundSerializer(many=True, read_only=True)

    class Meta:
        model = PaymentTransaction
        fields = (
            "id", "customer", "customer_name", "cash_amount", "transfer_amount",
            "total_amount", "refunded_amount", "refundable_amount", "allocations",
            "refunds", "created_at",
        )
        read_only_fields = fields
