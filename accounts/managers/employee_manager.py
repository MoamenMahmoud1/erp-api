from django.db import models

from accounts.querysets import EmployeeQuerySet


class EmployeeManager(models.Manager.from_queryset(EmployeeQuerySet)):
    pass
