from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from accounts.models import Employee, Role


User = get_user_model()


class UserSummarySerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = (
            "id",
            "username",
            "email",
            "first_name",
            "last_name",
            "is_active",
            "is_staff",
        )


class EmployeeSerializer(serializers.ModelSerializer):
    user_details = UserSummarySerializer(
        source="user",
        read_only=True,
    )
    manager_details = UserSummarySerializer(
        source="manager.user",
        read_only=True,
    )
    work_site_name = serializers.CharField(
        source="work_site.name",
        read_only=True,
        allow_null=True,
    )
    department_name = serializers.CharField(
        source="department.name",
        read_only=True,
        allow_null=True,
    )

    class Meta:
        model = Employee
        fields = (
            "id",
            "user",
            "user_details",
            "manager",
            "manager_details",
            "work_site",
            "work_site_name",
            "department",
            "department_name",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "created_at",
            "updated_at",
        )

    def validate(self, attrs):
        request = self.context.get("request")
        actor = getattr(request, "user", None)

        user = attrs.get(
            "user",
            getattr(self.instance, "user", None),
        )
        manager = attrs.get(
            "manager",
            getattr(self.instance, "manager", None),
        )
        work_site = attrs.get(
            "work_site",
            getattr(self.instance, "work_site", None),
        )
        department = attrs.get(
            "department",
            getattr(self.instance, "department", None),
        )

        if actor and user and not Role.can_manage_user(actor, user):
            raise ValidationError(
                {
                    "user": (
                        "You cannot manage an employee with "
                        "an equal or higher role."
                    )
                }
            )

        if (
            manager
            and not Employee.objects.visible_to(actor)
            .filter(pk=manager.pk)
            .exists()
        ):
            raise ValidationError(
                {
                    "manager": (
                        "You cannot assign a manager outside "
                        "your visible employee tree."
                    )
                }
            )

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
            raise ValidationError(
                exc.message_dict
            ) from exc

        return attrs
