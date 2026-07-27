from rest_framework import serializers
from django.contrib.auth import get_user_model

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

        user = attrs.get("user", getattr(self.instance, "user", None))
        manager = attrs.get("manager", getattr(self.instance, "manager", None))

        if actor and user and not Role.can_manage_user(actor, user):
            raise serializers.ValidationError(
                {"user": "You cannot manage an employee with an equal or higher role."}
            )

        if manager and not Employee.objects.visible_to(actor).filter(pk=manager.pk).exists():
            raise serializers.ValidationError(
                {"manager": "You cannot assign a manager outside your visible employee tree."}
            )

        return attrs
