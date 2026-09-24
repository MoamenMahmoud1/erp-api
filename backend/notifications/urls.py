from django.urls import path

from .views import (
    NotificationListView,
    NotificationMarkAllReadView,
    NotificationMarkReadView,
    PushDeviceRegistrationDeleteView,
    PushDeviceRegistrationView,
)

app_name = "notifications"

urlpatterns = [
    path("", NotificationListView.as_view(), name="list"),
    path("read-all/", NotificationMarkAllReadView.as_view(), name="read-all"),
    path("<int:pk>/read/", NotificationMarkReadView.as_view(), name="read"),
    path("devices/", PushDeviceRegistrationView.as_view(), name="device-register"),
    path("devices/<str:installation_id>/", PushDeviceRegistrationDeleteView.as_view(), name="device-delete"),
]
