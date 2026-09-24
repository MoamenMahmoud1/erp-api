from django.utils import timezone
from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Notification, PushDevice
from .serializers import NotificationSerializer, PushDeviceRegistrationSerializer


class NotificationListView(generics.ListAPIView):
    permission_classes = (IsAuthenticated,)
    serializer_class = NotificationSerializer

    def get_queryset(self):
        queryset = Notification.objects.filter(user=self.request.user)
        if self.request.query_params.get("unread") in {"1", "true", "True"}:
            queryset = queryset.filter(read_at__isnull=True)
        return queryset.order_by("-created_at", "-id")


class NotificationMarkReadView(APIView):
    permission_classes = (IsAuthenticated,)

    def post(self, request, pk):
        notification = Notification.objects.filter(
            pk=pk,
            user=request.user,
        ).first()
        if notification is None:
            return Response({"detail": "Notification not found."}, status=status.HTTP_404_NOT_FOUND)
        if notification.read_at is None:
            notification.read_at = timezone.now()
            notification.save(update_fields=("read_at",))
        return Response(NotificationSerializer(notification).data)


class NotificationMarkAllReadView(APIView):
    permission_classes = (IsAuthenticated,)

    def post(self, request):
        updated = Notification.objects.filter(
            user=request.user,
            read_at__isnull=True,
        ).update(read_at=timezone.now())
        return Response({"updated": updated})


class PushDeviceRegistrationView(APIView):
    permission_classes = (IsAuthenticated,)

    def post(self, request):
        serializer = PushDeviceRegistrationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        installation_id = serializer.validated_data["installation_id"]
        device, created = PushDevice.objects.get_or_create(
            installation_id=installation_id,
            defaults={
                "user": request.user,
                "platform": serializer.validated_data["platform"],
                "firebase_app_id": serializer.validated_data.get("firebase_app_id", ""),
            },
        )

        if not created and device.user_id != request.user.pk:
            device.user = request.user
            device.save(update_fields=("user", "updated_at"))

        device.touch(
            platform=serializer.validated_data["platform"],
            firebase_app_id=serializer.validated_data.get("firebase_app_id", ""),
        )
        return Response(
            {
                "installation_id": device.installation_id,
                "platform": device.platform,
                "is_active": device.is_active,
            },
            status=status.HTTP_200_OK if not created else status.HTTP_201_CREATED,
        )


class PushDeviceRegistrationDeleteView(APIView):
    permission_classes = (IsAuthenticated,)

    def delete(self, request, installation_id):
        device = PushDevice.objects.filter(
            installation_id=installation_id,
            user=request.user,
        ).first()
        if device is None:
            return Response(status=status.HTTP_204_NO_CONTENT)
        device.deactivate("Unregistered by authenticated user.")
        return Response(status=status.HTTP_204_NO_CONTENT)
