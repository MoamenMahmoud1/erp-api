import logging
from urllib.parse import urlencode

from django.conf import settings
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode

logger = logging.getLogger(__name__)


def _frontend_url(path, **query):
    base_url = settings.FRONTEND_URL.rstrip("/")
    url = f"{base_url}/{path.lstrip('/')}"
    return f"{url}?{urlencode(query)}" if query else url


def _send_email(*, subject, recipient, template_name, context):
    try:
        text_body = render_to_string(f"{template_name}.txt", context)
        html_body = render_to_string(f"{template_name}.html", context)
        message = EmailMultiAlternatives(
            subject=subject,
            body=text_body,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=(recipient,),
        )
        message.attach_alternative(html_body, "text/html")
        message.send()
    except Exception:
        logger.exception("Could not send account email.")


def send_password_reset_email(user):
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    token = default_token_generator.make_token(user)
    reset_url = _frontend_url(
        "reset-password",
        uid=uid,
        token=token,
    )
    _send_email(
        subject="Reset your password",
        recipient=user.email,
        template_name="accounts/emails/password_reset",
        context={
            "user": user,
            "reset_url": reset_url,
        },
    )


def send_signup_verification_email(user, verification):
    verification_url = _frontend_url(
        "verify-email",
        token=verification.token,
    )
    _send_email(
        subject="Verify your email",
        recipient=verification.email,
        template_name="accounts/emails/verify_email",
        context={
            "user": user,
            "verification_url": verification_url,
        },
    )


def send_email_change_verification(user, verification):
    verification_url = _frontend_url(
        "confirm-email-change",
        token=verification.token,
    )
    _send_email(
        subject="Confirm your new email",
        recipient=verification.email,
        template_name="accounts/emails/confirm_email_change",
        context={
            "user": user,
            "new_email": verification.email,
            "verification_url": verification_url,
        },
    )


def send_email_changed_notice(*, user, old_email, new_email):
    _send_email(
        subject="Your account email was changed",
        recipient=old_email,
        template_name="accounts/emails/email_changed",
        context={
            "user": user,
            "new_email": new_email,
        },
    )
