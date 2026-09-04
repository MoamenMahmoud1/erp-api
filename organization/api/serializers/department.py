from django.core.exceptions import ValidationError as DjangoValidationError
from adrf import serializers
from asgiref.sync import sync_to_async

from organization.models import Department


class DepartmentSerializer(serializers.ModelSerializer):
    company_name = serializers.CharField(
        source="company.name",
        read_only=True,
    )
    site_name = serializers.CharField(
        source="site.name",
        read_only=True,
        allow_null=True,
    )

    class Meta:
        model = Department
        fields = (
            "id",
            "company",
            "company_name",
            "site",
            "site_name",
            "code",
            "name",
            "description",
            "is_active",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "id",
            "company",
            "created_at",
            "updated_at",
        )

    def create(self, validated_data):
        try:
            return super().create(validated_data)
        except DjangoValidationError as exc:
            raise serializers.ValidationError(
                exc.message_dict
            ) from exc

    def update(self, instance, validated_data):
        try:
            return super().update(instance, validated_data)
        except DjangoValidationError as exc:
            raise serializers.ValidationError(
                exc.message_dict
            ) from exc

    async def acreate(self, validated_data):
        return await sync_to_async(self.create, thread_sensitive=True)(validated_data)

    async def aupdate(self, instance, validated_data):
        return await sync_to_async(
            self.update,
            thread_sensitive=True,
        )(instance, validated_data)
