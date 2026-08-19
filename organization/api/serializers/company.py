from rest_framework import serializers

from organization.models import Company


class CompanySerializer(serializers.ModelSerializer):
    class Meta:
        model = Company
        fields = (
            "id",
            "name",
            "legal_name",
            "registration_number",
            "tax_number",
            "email",
            "phone",
            "website",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "id",
            "created_at",
            "updated_at",
        )