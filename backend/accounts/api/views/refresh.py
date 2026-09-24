from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_protect
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from authsession.http import (
    NoStoreResponseMixin,
    clear_login_cookies,
    get_client_context,
    get_device_id,
    set_refresh_cookie,
)
from authsession.services.auth_session import InvalidAuthSession, refresh_auth_session
from authentication.throttling import RefreshBurstThrottle


def invalid_session_response():
    response = Response(
        {
            "detail": "Invalid or expired session.",
            "code": "invalid_session",
        },
        status=status.HTTP_401_UNAUTHORIZED,
    )
    clear_login_cookies(response)
    return response


@method_decorator(csrf_protect, name="dispatch")
class RefreshView(NoStoreResponseMixin, APIView):
    authentication_classes = ()
    permission_classes = (AllowAny,)
    throttle_classes = (RefreshBurstThrottle,)

    def post(self, request, *args, **kwargs):
        refresh_token = request.COOKIES.get("refresh_token")
        device_id = get_device_id(request)

        if not refresh_token or device_id is None:
            return invalid_session_response()

        try:
            result = refresh_auth_session(
                refresh_token=refresh_token,
                client_context=get_client_context(
                    request,
                    device_id=device_id,
                ),
            )
        except InvalidAuthSession:
            return invalid_session_response()

        response = Response(
            {"access": result.access_token},
            status=status.HTTP_200_OK,
        )
        set_refresh_cookie(
            response,
            refresh_token=result.refresh_token,
            max_age=result.refresh_max_age,
        )
        return response
