from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers

from accounts.models import RoleProfile
from organization.models import Site
from services.organization_scope import visible_site_ids


class SiteSerializer(serializers.ModelSerializer):
    company_name = serializers.CharField(
        source="company.name",
        read_only=True,
    )
    parent_name = serializers.CharField(
        source="parent.name",
        read_only=True,
        allow_null=True,
    )

    class Meta:
        model = Site
        fields = (
            "id",
            "company",
            "company_name",
            "parent",
            "parent_name",
            "code",
            "name",
            "site_type",
            "address_line_1",
            "address_line_2",
            "city",
            "state_or_province",
            "postal_code",
            "country_code",
            "email",
            "phone",
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

    def validate(self, attrs):
        request = self.context.get("request")
        actor = getattr(request, "user", None)
        parent = attrs.get("parent", getattr(self.instance, "parent", None))
        site_ids = visible_site_ids(actor) if actor else None
        actor_scope = RoleProfile.scope_for_user(actor) if actor else RoleProfile.Scope.SITE
        if self.instance is None and actor and not actor.is_superuser:
            if actor_scope == RoleProfile.Scope.SITE:
                raise serializers.ValidationError({"site_type": "Site-scoped users cannot create organizational sites."})
            if actor_scope == RoleProfile.Scope.BRANCH and parent is None:
                raise serializers.ValidationError({"parent": "Branch-scoped users must create sites under their visible branch."})
        if parent is not None and site_ids is not None:
            if not Site.objects.filter(pk=parent.pk, pk__in=site_ids).exists():
                raise serializers.ValidationError({"parent": "The parent site is outside your allowed scope."})
        return attrs

    def create(self, validated_data):
        try:
            return super().create(validated_data)
        except DjangoValidationError as exc:
            raise serializers.ValidationError(exc.message_dict) from exc

    def update(self, instance, validated_data):
        try:
            return super().update(instance, validated_data)
        except DjangoValidationError as exc:
            raise serializers.ValidationError(exc.message_dict) from exc
