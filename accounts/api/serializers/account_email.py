from functools import partial

from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import IntegrityError, transaction
from rest_framework import serializers

from accounts.services import (
    EmailUnavailable,
    InvalidEmailVerification,
    confirm_email_change,
    consume_signup_verification,
    issue_email_change,
    issue_signup_verification,
    send_email_change_verification,
    send_email_changed_notice,
    send_signup_verification_email,
)

User = get_user_model()


class SignUpSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)
    password_confirm = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = (
            "username",
            "email",
            "first_name",
            "last_name",
            "password",
            "password_confirm",
        )

    def validate(self, attrs):
        if attrs["password"] != attrs["password_confirm"]:
            raise serializers.ValidationError(
                {"password_confirm": "Passwords do not match."}
            )

        candidate = User(
            username=attrs["username"],
            email=attrs["email"],
            first_name=attrs.get("first_name", ""),
            last_name=attrs.get("last_name", ""),
        )
        try:
            validate_password(attrs["password"], user=candidate)
        except DjangoValidationError as error:
            raise serializers.ValidationError(
                {"password": error.messages}
            ) from error
        return attrs

    def create(self, validated_data):
        validated_data.pop("password_confirm")
        password = validated_data.pop("password")

        try:
            with transaction.atomic():
                user = User.objects.create_user(
                    **validated_data,
                    password=password,
                    is_active=False,
                    is_verified=False,
                )
                verification = issue_signup_verification(user)
                transaction.on_commit(
                    partial(send_signup_verification_email, user, verification)
                )
        except IntegrityError as error:
            errors = {}
            if User.objects.filter(username=validated_data["username"]).exists():
                errors["username"] = "This username is unavailable."
            if User.objects.filter(email__iexact=validated_data["email"]).exists():
                errors["email"] = "This email is unavailable."
            if errors:
                raise serializers.ValidationError(errors) from error
            raise

        return user


class EmailVerificationSerializer(serializers.Serializer):
    token = serializers.CharField(write_only=True)

    def save(self, **kwargs):
        try:
            return consume_signup_verification(self.validated_data["token"])
        except InvalidEmailVerification as error:
            raise serializers.ValidationError(
                {"token": "Invalid or expired email verification token."}
            ) from error


class EmailVerificationResendSerializer(serializers.Serializer):
    email = serializers.EmailField(write_only=True)

    def save(self, **kwargs):
        user = User.objects.filter(
            email__iexact=self.validated_data["email"],
            is_active=False,
            is_verified=False,
        ).first()
        if user is None:
            return None

        verification = issue_signup_verification(user)
        send_signup_verification_email(user, verification)
        return user


class EmailChangeRequestSerializer(serializers.Serializer):
    new_email = serializers.EmailField(write_only=True)

    def validate_new_email(self, value):
        new_email = User.objects.normalize_email(value)
        if new_email.casefold() == self.context["request"].user.email.casefold():
            raise serializers.ValidationError("The new email must be different.")
        return new_email

    def save(self, **kwargs):
        user = self.context["request"].user
        try:
            verification = issue_email_change(
                user=user,
                new_email=self.validated_data["new_email"],
            )
        except EmailUnavailable as error:
            raise serializers.ValidationError(
                {"new_email": "This email is unavailable."}
            ) from error

        send_email_change_verification(user, verification)
        return verification


class EmailChangeConfirmSerializer(serializers.Serializer):
    token = serializers.CharField(write_only=True)

    def save(self, **kwargs):
        try:
            confirmed = confirm_email_change(self.validated_data["token"])
        except (InvalidEmailVerification, EmailUnavailable) as error:
            raise serializers.ValidationError(
                {"token": "Invalid or expired email change token."}
            ) from error

        send_email_changed_notice(
            user=confirmed.user,
            old_email=confirmed.old_email,
            new_email=confirmed.new_email,
        )
        return confirmed
