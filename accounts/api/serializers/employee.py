from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from accounts.models import Employee, Role
from organization.models import Department, Site
from services.organization_scope import visible_site_ids


User = get_user_model()


class RoleSummarySerializer(serializers.ModelSerializer):
    name = serializers.CharField(source="group.name", read_only=True)

    class Meta:
        model = Role
        fields = ("code", "name", "level", "scope", "requires_shift")
        read_only_fields = fields


class GroupSummarySerializer(serializers.ModelSerializer):
    role = RoleSummarySerializer(source="role_profile", read_only=True)

    class Meta:
        model = Group
        fields = ("id", "name", "role")
        read_only_fields = fields


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
        roles = []
        for group in obj.groups.all():
            role = getattr(group, "role_profile", None)
            if role is not None:
                roles.append(role)
        return sorted(roles, key=lambda item: (-item.level, item.code))

    def get_roles(self, obj):
        return RoleSummarySerializer(self._get_roles(obj), many=True).data

    def get_role(self, obj):
        roles = self._get_roles(obj)
        role = roles[0] if roles else None
        return RoleSummarySerializer(role).data if role else None


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
    groups = GroupSummarySerializer(source="user.groups", many=True, read_only=True)
    group_ids = serializers.PrimaryKeyRelatedField(
        many=True,
        queryset=Group.objects.filter(role_profile__isnull=False).select_related("role_profile"),
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
            "groups",
        )

    def validate(self, attrs):
        request = self.context.get("request")
        actor = getattr(request, "user", None)
        user = attrs.get("user", getattr(self.instance, "user", None))
        manager = attrs.get("manager", getattr(self.instance, "manager", None))
        work_site = attrs.get("work_site", getattr(self.instance, "work_site", None))
        department = attrs.get("department", getattr(self.instance, "department", None))
        requested_groups = attrs.get("group_ids", serializers.empty)

        if actor and user and not Role.can_manage_user(actor, user):
            raise ValidationError({"user": "You cannot manage an employee with an equal or higher role."})

        if requested_groups is not serializers.empty and actor and not actor.is_superuser:
            actor_level = Role.level_for_user(actor)
            invalid_groups = [
                group
                for group in requested_groups
                if getattr(group, "role_profile", None) is None
                or group.role_profile.level >= actor_level
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
        actor_scope = Role.scope_for_user(actor) if actor else Role.Scope.SITE
        if work_site and actor_scope != Role.Scope.COMPANY:
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

    @transaction.atomic
    def create(self, validated_data):
        groups = validated_data.pop("group_ids", serializers.empty)
        employee = super().create(validated_data)
        if groups is not serializers.empty:
            employee.user.groups.set(groups)
        return employee

    @transaction.atomic
    def update(self, instance, validated_data):
        groups = validated_data.pop("group_ids", serializers.empty)
        employee = super().update(instance, validated_data)
        if groups is not serializers.empty:
            employee.user.groups.set(groups)
        return employee
