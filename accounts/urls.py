from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .api.views import EmployeeViewSet, RoleViewSet
from .api.views.current_user import CurrentUserView
from .api.views.login import CsrfTokenView, LoginView
from .api.views.logout import LogoutAllView, LogoutView
from .api.views.password_change import PasswordChangeView
from .api.views.password_reset import PasswordResetConfirmView, PasswordResetRequestView
from .api.views.refresh import RefreshView
from .api.views.shift import CloseEmployeeShiftView, CurrentEmployeeShiftView, EmployeeShiftListView, EmployeeShiftVehicleOptionsView, StartEmployeeShiftView
from .api.views.account_email import EmailChangeConfirmView, EmailChangeRequestView, EmailVerificationResendView, EmailVerificationView, SignUpView

app_name = "accounts"

router = DefaultRouter()
router.register("employees", EmployeeViewSet, basename="employee")
router.register("roles", RoleViewSet, basename="role")

urlpatterns = [
    path("auth/me/", CurrentUserView.as_view(), name="current-user"),
    path("auth/csrf/", CsrfTokenView.as_view(), name="csrf-token"),
    path("auth/signup/", SignUpView.as_view(), name="signup"),
    path("auth/email/verify/", EmailVerificationView.as_view(), name="email-verify"),
    path("auth/email/verification/resend/", EmailVerificationResendView.as_view(), name="email-verification-resend"),
    path("auth/email/change/", EmailChangeRequestView.as_view(), name="email-change"),
    path("auth/email/change/confirm/", EmailChangeConfirmView.as_view(), name="email-change-confirm"),
    path("auth/login/", LoginView.as_view(), name="login"),
    path("auth/refresh/", RefreshView.as_view(), name="refresh"),
    path("auth/logout/", LogoutView.as_view(), name="logout"),
    path("auth/logout-all/", LogoutAllView.as_view(), name="logout-all"),
    path("auth/password/change/", PasswordChangeView.as_view(), name="password-change"),
    path("auth/password-reset/", PasswordResetRequestView.as_view(), name="password-reset"),
    path("auth/password-reset/confirm/", PasswordResetConfirmView.as_view(), name="password-reset-confirm"),
    path("auth/", include("authsession.urls")),
    path("shifts/current/", CurrentEmployeeShiftView.as_view(), name="shift-current"),
    path("shifts/vehicles/", EmployeeShiftVehicleOptionsView.as_view(), name="shift-vehicles"),
    path("shifts/start/", StartEmployeeShiftView.as_view(), name="shift-start"),
    path("shifts/close/", CloseEmployeeShiftView.as_view(), name="shift-close"),
    path("shifts/", EmployeeShiftListView.as_view(), name="shift-list"),
] + router.urls
