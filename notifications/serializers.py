from rest_framework import serializers

from .models import Notification, PushDevice


class NotificationSerializer(serializers.ModelSerializer):
    is_read = serializers.BooleanField(read_only=True)

    class Meta:
        model = Notification
        fields = (
            "id",
            "notification_type",
            "title",
            "body",
            "target_type",
            "target_id",
            "data",
            "is_read",
            "read_at",
            "created_at",
        )
        read_only_fields = fields


class PushDeviceRegistrationSerializer(serializers.Serializer):
    installation_id = serializers.CharField(min_length=1, max_length=255)
    platform = serializers.ChoiceField(choices=PushDevice.Platform.choices)
    firebase_app_id = serializers.CharField(required=False, allow_blank=True, max_length=255)
