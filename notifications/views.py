from django.utils import timezone
from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Notification
from .serializers import NotificationSerializer


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
