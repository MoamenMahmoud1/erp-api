from adrf import serializers
from asgiref.sync import sync_to_async

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

    async def get_is_current(self, auth_session) -> bool:
        request = self.context.get("request")
        return bool(
            request
            and get_device_id(request) == auth_session.device_id
        )

    async def acreate(self, validated_data):
        return await sync_to_async(self.create, thread_sensitive=True)(validated_data)

    async def aupdate(self, instance, validated_data):
        return await sync_to_async(
            self.update,
            thread_sensitive=True,
        )(instance, validated_data)


class AuthSessionVerificationSerializer(serializers.Serializer):
    current_password = serializers.CharField(write_only=True)
