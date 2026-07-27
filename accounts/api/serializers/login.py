from django.contrib.auth import authenticate
from rest_framework import serializers
from rest_framework.exceptions import AuthenticationFailed


class LoginSerializer(serializers.Serializer):
    identifier = serializers.CharField(max_length=254, write_only=True)
    password = serializers.CharField(write_only=True)

    default_error_messages = {
        "no_active_account": "Invalid login credentials.",
    }

    def validate(self, attrs):
        user = authenticate(
            request=self.context.get("request"),
            username=attrs["identifier"],
            password=attrs["password"],
        )
        if user is None:
            raise AuthenticationFailed(
                self.error_messages["no_active_account"],
                code="no_active_account",
            )

        self.user = user
        return {}
