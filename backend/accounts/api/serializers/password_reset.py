from django.contrib.auth import get_user_model
from django.contrib.auth.forms import PasswordResetForm
from django.contrib.auth.password_validation import validate_password
from django.contrib.auth.tokens import default_token_generator
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from django.utils.encoding import force_str
from django.utils.http import urlsafe_base64_decode
from rest_framework import serializers

from accounts.services import send_password_reset_email
from authsession.services.auth_session import revoke_all_sessions

User = get_user_model()


class PasswordResetRequestSerializer(serializers.Serializer):
    email = serializers.EmailField(write_only=True)

    def save(self, **kwargs):
        user = next(
            PasswordResetForm().get_users(self.validated_data["email"]),
            None,
        )
        if user is not None:
            send_password_reset_email(user)


class PasswordResetConfirmSerializer(serializers.Serializer):
    uid = serializers.CharField(write_only=True)
    token = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True)

    default_error_messages = {
        "invalid_token": "Invalid or expired password reset token.",
    }

    def _user_id(self, uid):
        try:
            return force_str(urlsafe_base64_decode(uid))
        except (TypeError, ValueError, OverflowError, UnicodeDecodeError):
            self.fail("invalid_token")

    def validate(self, attrs):
        user_id = self._user_id(attrs["uid"])
        user = User.objects.filter(pk=user_id, is_active=True).first()
        if user is None or not default_token_generator.check_token(
            user,
            attrs["token"],
        ):
            self.fail("invalid_token")

        try:
            validate_password(attrs["new_password"], user=user)
        except DjangoValidationError as error:
            raise serializers.ValidationError(
                {"new_password": error.messages}
            ) from error

        return attrs

    def save(self, **kwargs):
        user_id = self._user_id(self.validated_data["uid"])
        with transaction.atomic():
            user = (
                User.objects.select_for_update()
                .filter(pk=user_id, is_active=True)
                .first()
            )
            if user is None or not default_token_generator.check_token(
                user,
                self.validated_data["token"],
            ):
                self.fail("invalid_token")

            user.set_password(self.validated_data["new_password"])
            user.save(update_fields=("password", "password_changed_at", "updated_at"))
            revoke_all_sessions(user_id=user_id)

        return user
