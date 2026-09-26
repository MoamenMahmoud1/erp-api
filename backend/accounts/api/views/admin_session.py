from django.contrib.auth import get_user_model, login as django_login
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_protect
from rest_framework import status
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from authsession.constants import ADMIN_AUTH_SESSION_SESSION_KEY
from authsession.http import NoStoreResponseMixin
from authsession.permissions import CurrentAuthSessionPermission


@method_decorator(csrf_protect, name="dispatch")
class AdminSessionView(NoStoreResponseMixin, APIView):
    """Bridge the authenticated ERP session into a Django Admin session."""

    permission_classes = (IsAuthenticated, CurrentAuthSessionPermission)

    def post(self, request, *args, **kwargs):
        if not request.user.is_superuser:
            raise PermissionDenied("Django Admin access is restricted to superusers.")

        user_model = get_user_model()
        try:
            user = user_model.objects.get(
                pk=request.user.pk,
                is_active=True,
                is_superuser=True,
            )
        except user_model.DoesNotExist as error:
            raise PermissionDenied("Django Admin access is restricted to superusers.") from error

        django_login(
            request,
            user,
            backend="django.contrib.auth.backends.ModelBackend",
        )
        request.session[ADMIN_AUTH_SESSION_SESSION_KEY] = str(
            request.auth_session.pk
        )

        return Response(
            {"url": request.build_absolute_uri(reverse("admin:index"))},
            status=status.HTTP_200_OK,
        )
