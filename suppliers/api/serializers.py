from rest_framework import serializers

from suppliers.models import Supplier


class SupplierSerializer(serializers.ModelSerializer):
    class Meta:
        model = Supplier
        fields = (
            "id",
            "name",
            "phone",
            "email",
            "address",
            "is_active",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "id",
            "created_at",
            "updated_at",
        )

    def create(self, validated_data):
        return Supplier.objects.create(**validated_data)

    def update(self, instance, validated_data):
        for attribute, value in validated_data.items():
            setattr(instance, attribute, value)
        instance.save()
        return instance
