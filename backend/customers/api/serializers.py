from rest_framework import serializers

from customers.models import Customer
from customers.services.create import create_customer_sync
from customers.services.update import update_customer_sync


class CustomerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Customer
        fields = "__all__"
        read_only_fields = ("id", "created_at", "updated_at")

    def create(self, validated_data):
        return create_customer_sync(validated_data)

    def update(self, instance, validated_data):
        return update_customer_sync(instance, validated_data)
