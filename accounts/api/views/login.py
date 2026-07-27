from django.middleware.csrf import get_token
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_protect
from rest_framework import status
from rest_framework.generics import GenericAPIView
from rest_framework.parsers import JSONParser
from rest_framework.permissions import AllowAny
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.api.serializers.login import LoginSerializer
from authsession.http import (
    NoStoreResponseMixin,
    get_client_context,
    set_login_cookies,
)
from authentication.throttling import LoginBurstThrottle, LoginSustainedThrottle
from authsession.services.auth_session import InvalidAuthSession, start_auth_session


class CsrfTokenView(NoStoreResponseMixin, APIView):
    authentication_classes = ()
    permission_classes = (AllowAny,)

    def get(self, request, *args, **kwargs):
        return Response({"csrf_token": get_token(request)})


@method_decorator(csrf_protect, name="dispatch")
class LoginView(NoStoreResponseMixin, GenericAPIView):
    serializer_class = LoginSerializer
    authentication_classes = ()
    permission_classes = (AllowAny,)
    parser_classes = (JSONParser,)
    throttle_classes = (LoginBurstThrottle, LoginSustainedThrottle)

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            login_result = start_auth_session(
                user=serializer.user,
                client_context=get_client_context(request),
            )
        except InvalidAuthSession as error:
            raise AuthenticationFailed(
                "Invalid login credentials.",
                code="no_active_account",
            ) from error

        response = Response(
            {"access": login_result.access_token},
            status=status.HTTP_200_OK,
        )
        set_login_cookies(
            response,
            refresh_token=login_result.refresh_token,
            device_id=login_result.device_id,
        )
        return response
