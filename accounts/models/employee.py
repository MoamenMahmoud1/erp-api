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


    work_site = models.ForeignKey(
        "organization.Site",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="employees",
        )


    department = models.ForeignKey(
        "organization.Department",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="employees",
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
        if not self.department_id:
            return
        
        department = self.department
        work_site = self.work_site if self.work_site_id else None
        
        if work_site and department.company_id != work_site.company_id:
            raise ValidationError(
                {
                    "department": (
                        "The department and work site must belong "
                        "to the same company."
                    )
                }
            )
        
        if not department.site_id:
            return
        
        if not work_site:
            raise ValidationError(
                {
                    "work_site": (
                        "An employee in a site-specific department "
                        "must have a work site."
                    )
                }
            )
        
        works_at_department_site = work_site.pk == department.site_id
        
        works_at_child_store = (
            work_site.site_type == "store"
            and work_site.parent_id == department.site_id
        )
        
        if not works_at_department_site and not works_at_child_store:
            raise ValidationError(
                {
                    "department": (
                        "The department must belong to the employee's "
                        "work site or its parent branch."
                    )
                }
            )

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)
