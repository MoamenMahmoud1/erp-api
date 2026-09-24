from rest_framework.throttling import AnonRateThrottle, UserRateThrottle

from authsession.http import get_client_ip


class ClientIPThrottleMixin:
    def get_ident(self, request):
        return get_client_ip(request) or super().get_ident(request)


class LoginBurstThrottle(ClientIPThrottleMixin, AnonRateThrottle):
    scope = "login_burst"


class LoginSustainedThrottle(ClientIPThrottleMixin, AnonRateThrottle):
    scope = "login_sustained"


class RefreshBurstThrottle(ClientIPThrottleMixin, AnonRateThrottle):
    scope = "refresh_burst"


class PasswordResetThrottle(ClientIPThrottleMixin, AnonRateThrottle):
    scope = "password_reset"


class SignUpThrottle(ClientIPThrottleMixin, AnonRateThrottle):
    scope = "signup"


class EmailActionThrottle(ClientIPThrottleMixin, UserRateThrottle):
    scope = "email_action"


class SensitiveActionThrottle(ClientIPThrottleMixin, UserRateThrottle):
    scope = "sensitive_action"
