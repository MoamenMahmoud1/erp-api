from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from rest_framework import serializers

from authsession.services.auth_session import revoke_all_sessions

User = get_user_model()


class PasswordChangeSerializer(serializers.Serializer):
    new_password = serializers.CharField(write_only=True)
    password_confirm = serializers.CharField(write_only=True)

    def validate(self, attrs):
        if attrs["new_password"] != attrs["password_confirm"]:
            raise serializers.ValidationError(
                {"password_confirm": "Passwords do not match."}
            )
        try:
            validate_password(
                attrs["new_password"],
                user=self.context["request"].user,
            )
        except DjangoValidationError as error:
            raise serializers.ValidationError(
                {"new_password": error.messages}
            ) from error
        return attrs

    def save(self, **kwargs):
        with transaction.atomic():
            user = User.objects.select_for_update().get(
                pk=self.context["request"].user.pk
            )
            user.set_password(self.validated_data["new_password"])
            user.save(update_fields=("password", "password_changed_at", "updated_at"))
            revoke_all_sessions(user)
        return user
