from django.contrib.auth.models import AbstractUser
from django.db import models
from django.db.models.functions import Lower
from django.utils import timezone

from phonenumber_field.modelfields import PhoneNumberField

from accounts.managers import CustomUserManager


class CustomUserModel(AbstractUser):
    email = models.EmailField()
    phone_number = PhoneNumberField(blank=True, null=True)
    is_verified = models.BooleanField(default=False)
    photo = models.ImageField(upload_to="photo/%Y/%m/%d/", null=True, blank=True)
    password_changed_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    REQUIRED_FIELDS = ["email"]
    objects = CustomUserManager()

    def set_password(self, raw_password):
        super().set_password(raw_password)
        self.password_changed_at = timezone.now()

    class Meta:
        verbose_name = "User"
        verbose_name_plural = "Users"

        constraints = [
            models.CheckConstraint(
                condition=~models.Q(username__contains="@"),
                name="accounts_user_username_not_at",
            ),
            models.CheckConstraint(
                condition=~models.Q(email=""),
                name="accounts_user_email_not_empty",
            ),
            models.UniqueConstraint(
                Lower("email"),
                name="accounts_user_email_ci_unique",
            ),
        ]

    def __str__(self):
        return self.username
