from decimal import Decimal

from rest_framework import serializers

from customers.models import Customer
from payments.models import PaymentAllocation, PaymentTransaction


class CollectionSerializer(serializers.Serializer):
    """Client input for a collection.

    The client reports only the customer and how much cash/transfer was
    received — it must NOT choose invoice allocations.
    """

    customer = serializers.PrimaryKeyRelatedField(
        queryset=Customer.objects.all(),
    )
    cash_amount = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
        min_value=Decimal("0"),
        default=Decimal("0"),
    )
    transfer_amount = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
        min_value=Decimal("0"),
        default=Decimal("0"),
    )

    def validate(self, attrs):
        if attrs["cash_amount"] < 0 or attrs["transfer_amount"] < 0:
            raise serializers.ValidationError(
                {
                    "non_field_errors": (
                        "Cash and transfer amounts must not be negative."
                    )
                }
            )
        return attrs


class PaymentAllocationSerializer(serializers.ModelSerializer):
    invoice = serializers.PrimaryKeyRelatedField(read_only=True)

    class Meta:
        model = PaymentAllocation
        fields = (
            "id",
            "invoice",
            "cash_amount",
            "transfer_amount",
            "total_amount",
            "created_at",
        )
        read_only_fields = fields


class PaymentTransactionSerializer(serializers.ModelSerializer):
    customer_name = serializers.CharField(
        source="customer.name",
        read_only=True,
    )
    allocations = PaymentAllocationSerializer(many=True, read_only=True)

    class Meta:
        model = PaymentTransaction
        fields = (
            "id",
            "customer",
            "customer_name",
            "cash_amount",
            "transfer_amount",
            "total_amount",
            "allocations",
            "created_at",
        )
        read_only_fields = fields
