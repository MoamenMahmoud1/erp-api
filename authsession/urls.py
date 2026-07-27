from django.urls import path
from rest_framework.routers import SimpleRouter

from authsession.api.views import AuthSessionVerificationView, AuthSessionViewSet


router = SimpleRouter()
router.register("sessions", AuthSessionViewSet, basename="session")

urlpatterns = [
    path(
        "sessions/verify/",
        AuthSessionVerificationView.as_view(),
        name="session-verify",
    ),
] + router.urls
