from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError as DjangoValidationError
from adrf import serializers
from asgiref.sync import sync_to_async
from rest_framework.exceptions import ValidationError

from accounts.models import Employee, Role


User = get_user_model()


class UserSummarySerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = (
            "id",
            "username",
            "first_name",
            "last_name",
        )


class EmployeeSerializer(serializers.ModelSerializer):
    user_details = UserSummarySerializer(
        source="user",
        read_only=True,
    )

    class Meta:
        model = Employee
        fields = (
            "id",
            "user",
            "user_details",
            "manager",
            "work_site",
            "department",
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

    async def acreate(self, validated_data):
        return await sync_to_async(
            self.create,
            thread_sensitive=True,
        )(validated_data)

    async def aupdate(self, instance, validated_data):
        return await sync_to_async(
            self.update,
            thread_sensitive=True,
        )(instance, validated_data)
