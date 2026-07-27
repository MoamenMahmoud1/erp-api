import secrets
from dataclasses import dataclass

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core import signing
from django.db import IntegrityError, transaction

from authsession.services.auth_session import revoke_all_sessions

User = get_user_model()
SIGNUP_TOKEN_SALT = "accounts.signup-email-verification"
EMAIL_CHANGE_TOKEN_SALT = "accounts.email-change"


class InvalidEmailVerification(Exception):
    pass


class EmailUnavailable(Exception):
    pass


@dataclass(frozen=True, slots=True)
class IssuedEmailVerification:
    token: str
    email: str


@dataclass(frozen=True, slots=True)
class ConfirmedEmailChange:
    user: object
    old_email: str
    new_email: str


def issue_signup_verification(user):
    token = signing.dumps(
        {
            "user_id": user.pk,
            "email": user.email,
            "nonce": secrets.token_urlsafe(16),
        },
        salt=SIGNUP_TOKEN_SALT,
    )
    return IssuedEmailVerification(token=token, email=user.email)


def consume_signup_verification(token):
    try:
        payload = signing.loads(
            token,
            salt=SIGNUP_TOKEN_SALT,
            max_age=settings.EMAIL_VERIFICATION_TIMEOUT,
        )
    except signing.BadSignature as error:
        raise InvalidEmailVerification from error

    with transaction.atomic():
        try:
            user = User.objects.select_for_update().get(pk=payload["user_id"])
        except (KeyError, User.DoesNotExist) as error:
            raise InvalidEmailVerification from error

        if (
            user.is_verified
            or user.is_active
            or user.email.casefold() != str(payload.get("email", "")).casefold()
        ):
            raise InvalidEmailVerification

        user.is_active = True
        user.is_verified = True
        user.save(update_fields=("is_active", "is_verified", "updated_at"))

    return user


def issue_email_change(*, user, new_email):
    new_email = User.objects.normalize_email(new_email)
    if User.objects.filter(email__iexact=new_email).exclude(pk=user.pk).exists():
        raise EmailUnavailable

    token = signing.dumps(
        {
            "user_id": user.pk,
            "old_email": user.email,
            "new_email": new_email,
            "nonce": secrets.token_urlsafe(16),
        },
        salt=EMAIL_CHANGE_TOKEN_SALT,
    )
    return IssuedEmailVerification(token=token, email=new_email)


def confirm_email_change(token):
    try:
        payload = signing.loads(
            token,
            salt=EMAIL_CHANGE_TOKEN_SALT,
            max_age=settings.EMAIL_CHANGE_TIMEOUT,
        )
        user_id = payload["user_id"]
        old_email = str(payload["old_email"])
        new_email = User.objects.normalize_email(payload["new_email"])
    except (KeyError, TypeError, signing.BadSignature) as error:
        raise InvalidEmailVerification from error

    try:
        with transaction.atomic():
            user = User.objects.select_for_update().get(pk=user_id, is_active=True)
            if user.email.casefold() != old_email.casefold():
                raise InvalidEmailVerification
            if User.objects.filter(email__iexact=new_email).exclude(
                pk=user.pk
            ).exists():
                raise EmailUnavailable

            user.email = new_email
            user.is_verified = True
            user.save(update_fields=("email", "is_verified", "updated_at"))
            revoke_all_sessions(user)
    except User.DoesNotExist as error:
        raise InvalidEmailVerification from error
    except IntegrityError as error:
        raise EmailUnavailable from error

    return ConfirmedEmailChange(
        user=user,
        old_email=old_email,
        new_email=new_email,
    )
