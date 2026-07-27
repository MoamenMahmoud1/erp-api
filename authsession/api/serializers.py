from rest_framework import serializers

from authsession.http import get_device_id
from authsession.models import AuthSession


class AuthSessionSerializer(serializers.ModelSerializer):
    is_current = serializers.SerializerMethodField()

    class Meta:
        model = AuthSession
        fields = (
            "id",
            "device_name",
            "user_agent",
            "ip_address",
            "created_at",
            "last_refreshed_at",
            "expires_at",
            "is_current",
        )
        read_only_fields = fields

    def get_is_current(self, auth_session):
        request = self.context.get("request")
        return bool(
            request
            and get_device_id(request) == auth_session.device_id
        )


class AuthSessionVerificationSerializer(serializers.Serializer):
    current_password = serializers.CharField(write_only=True)
