from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models

from accounts.managers import EmployeeManager

class Employee(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="employee",
    )
    manager = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="team_members",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    objects = EmployeeManager()

    class Meta:
        verbose_name = "Employee"
        verbose_name_plural = "Employees"


    def __str__(self):
        return self.user.get_full_name() or self.user.username
    def clean(self):
        super().clean()

        if self.pk and self.manager_id == self.pk:
            raise ValidationError({"manager": "An employee cannot manage themselves."})

        if self.manager and self.pk:
            manager = self.manager
            visited = set()
            while manager:
                if manager.pk == self.pk or manager.pk in visited:
                    raise ValidationError(
                        {"manager": "The employee management tree cannot contain cycles."}
                    )
                visited.add(manager.pk)
                manager = manager.manager

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)
