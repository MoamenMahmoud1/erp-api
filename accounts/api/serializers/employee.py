from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from django.db.models import IntegerField, Value
from django.db.models.functions import Coalesce
from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from accounts.models import Employee, GroupPolicy
from organization.models import Department, Site
from services.organization_scope import visible_site_ids


User = get_user_model()


class RoleSummarySerializer(serializers.ModelSerializer):
    level = serializers.SerializerMethodField()
    scope = serializers.SerializerMethodField()
    requires_shift = serializers.SerializerMethodField()
    description = serializers.SerializerMethodField()

    class Meta:
        model = Group
        fields = ("id", "name", "level", "scope", "requires_shift", "description")
        read_only_fields = fields

    def get_level(self, obj):
        return GroupPolicy.level_for_group(obj)

    def get_scope(self, obj):
        return GroupPolicy.scope_for_group(obj)

    def get_requires_shift(self, obj):
        return GroupPolicy.requires_shift_for_group(obj)

    def get_description(self, obj):
        policy = getattr(obj, "policy", None)
        return policy.description if policy else ""


class GroupSummarySerializer(serializers.ModelSerializer):
    role = serializers.SerializerMethodField()

    class Meta:
        model = Group
        fields = ("id", "name", "role")
        read_only_fields = fields

    def get_role(self, obj):
        return RoleSummarySerializer(obj, context=self.context).data


class UserSummarySerializer(serializers.ModelSerializer):
    roles = serializers.SerializerMethodField()
    role = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = (
            "id",
            "username",
            "email",
            "first_name",
            "last_name",
            "phone_number",
            "is_active",
            "is_staff",
            "is_verified",
            "role",
            "roles",
        )

    @staticmethod
    def _get_roles(obj):
        return list(
            obj.groups.select_related("policy")
            .annotate(_role_level=Coalesce("policy__level", Value(0), output_field=IntegerField()))
            .order_by("-_role_level", "name", "pk")
        )

    def get_roles(self, obj):
        return RoleSummarySerializer(self._get_roles(obj), many=True, context=self.context).data

    def get_role(self, obj):
        groups = self._get_roles(obj)
        return RoleSummarySerializer(groups[0], context=self.context).data if groups else None


class SiteSummarySerializer(serializers.ModelSerializer):
    type = serializers.CharField(source="site_type", read_only=True)

    class Meta:
        model = Site
        fields = ("id", "name", "code", "type", "parent_id", "company_id", "is_active")
        read_only_fields = fields


class DepartmentSummarySerializer(serializers.ModelSerializer):
    class Meta:
        model = Department
        fields = ("id", "name", "code", "site_id", "company_id", "is_active")
        read_only_fields = fields


class EmployeeSerializer(serializers.ModelSerializer):
    user_details = UserSummarySerializer(source="user", read_only=True)
    manager_details = UserSummarySerializer(source="manager.user", read_only=True)
    role = serializers.SerializerMethodField()
    groups = GroupSummarySerializer(source="user.groups", many=True, read_only=True)
    role_id = serializers.PrimaryKeyRelatedField(
        source="_role_assignment",
        queryset=Group.objects.all().select_related("policy"),
        allow_null=True,
        required=False,
        write_only=True,
    )
    group_ids = serializers.PrimaryKeyRelatedField(
        many=True,
        queryset=Group.objects.all(),
        required=False,
        write_only=True,
    )
    work_site_name = serializers.CharField(source="work_site.name", read_only=True, allow_null=True)
    work_site_details = SiteSummarySerializer(source="work_site", read_only=True)
    department_name = serializers.CharField(source="department.name", read_only=True, allow_null=True)
    department_details = DepartmentSummarySerializer(source="department", read_only=True)

    class Meta:
        model = Employee
        fields = (
            "id",
            "user",
            "user_details",
            "role",
            "role_id",
            "groups",
            "group_ids",
            "manager",
            "manager_details",
            "work_site",
            "work_site_name",
            "work_site_details",
            "department",
            "department_name",
            "department_details",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "created_at",
            "updated_at",
            "work_site_name",
            "work_site_details",
            "department_name",
            "department_details",
            "manager_details",
            "user_details",
            "role",
            "groups",
        )

    @staticmethod
    def _highest_role(user):
        return GroupPolicy.highest_for_user(user)

    def get_role(self, obj):
        group = self._highest_role(obj.user)
        return RoleSummarySerializer(group, context=self.context).data if group else None

    def validate(self, attrs):
        request = self.context.get("request")
        actor = getattr(request, "user", None)
        user = attrs.get("user", getattr(self.instance, "user", None))
        manager = attrs.get("manager", getattr(self.instance, "manager", None))
        work_site = attrs.get("work_site", getattr(self.instance, "work_site", None))
        department = attrs.get("department", getattr(self.instance, "department", None))
        requested_role = attrs.get("_role_assignment", serializers.empty)
        requested_groups = attrs.get("group_ids", serializers.empty)

        if requested_role is not serializers.empty and requested_groups is not serializers.empty:
            raise ValidationError({"role_id": "Use role_id instead of group_ids when assigning an employee role."})

        if actor and user and not GroupPolicy.can_manage_user(actor, user):
            raise ValidationError({"user": "You cannot manage an employee with an equal or higher role."})

        if requested_role is not serializers.empty and requested_role is not None and actor and not actor.is_superuser:
            actor_level = GroupPolicy.level_for_user(actor)
            if GroupPolicy.level_for_group(requested_role) >= actor_level:
                raise ValidationError({"role_id": "You can only assign a role below your own role level."})

        if requested_groups is not serializers.empty and actor and not actor.is_superuser:
            actor_level = GroupPolicy.level_for_user(actor)
            invalid_groups = [
                group
                for group in requested_groups
                if GroupPolicy.level_for_group(group) >= actor_level
            ]
            if invalid_groups:
                raise ValidationError({"group_ids": "You can only assign groups whose roles are below your own role level."})

        if manager and not Employee.objects.visible_to(actor).filter(pk=manager.pk).exists():
            raise ValidationError({"manager": "You cannot assign a manager outside your visible employee tree."})

        if department and department.site_id and work_site and department.site_id != work_site.pk:
            allowed = bool(work_site.parent_id and department.site_id == work_site.parent_id)
            if not allowed:
                raise ValidationError({"department": "The department does not belong to the employee's site or parent branch."})

        site_ids = visible_site_ids(actor) if actor else None
        actor_scope = GroupPolicy.scope_for_user(actor) if actor else GroupPolicy.Scope.SITE
        if work_site and actor_scope != GroupPolicy.Scope.COMPANY:
            if site_ids is None or not work_site.__class__.objects.filter(pk=work_site.pk, pk__in=site_ids).exists():
                raise ValidationError({"work_site": "The work site is outside your allowed scope."})

        candidate = Employee(
            pk=getattr(self.instance, "pk", None),
            user=user,
            manager=manager,
            work_site=work_site,
            department=department,
        )
        try:
            candidate.clean()
        except DjangoValidationError as exc:
            raise ValidationError(exc.message_dict) from exc
        return attrs

    @staticmethod
    def _set_role_groups(user, group):
        user.groups.set([group] if group is not None else [])

    @staticmethod
    def _set_legacy_role_groups(user, groups):
        user.groups.set(groups)

    @transaction.atomic
    def create(self, validated_data):
        role = validated_data.pop("_role_assignment", serializers.empty)
        groups = validated_data.pop("group_ids", serializers.empty)
        employee = super().create(validated_data)
        if role is not serializers.empty:
            self._set_role_groups(employee.user, role)
        elif groups is not serializers.empty:
            self._set_legacy_role_groups(employee.user, groups)
        return employee

    @transaction.atomic
    def update(self, instance, validated_data):
        role = validated_data.pop("_role_assignment", serializers.empty)
        groups = validated_data.pop("group_ids", serializers.empty)
        employee = super().update(instance, validated_data)
        if role is not serializers.empty:
            self._set_role_groups(employee.user, role)
        elif groups is not serializers.empty:
            self._set_legacy_role_groups(employee.user, groups)
        return employee
