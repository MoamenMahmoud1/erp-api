from django.db import models
from django.db.models import Q


class CustomerAssignment(models.Model):
    customer = models.ForeignKey(
        "customers.Customer",
        on_delete=models.CASCADE,
        related_name="representative_assignments",
    )
    employee = models.ForeignKey(
        "accounts.Employee",
        on_delete=models.CASCADE,
        related_name="customer_assignments",
    )
    is_active = models.BooleanField(default=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("customer_id", "employee_id")
        constraints = [
            models.UniqueConstraint(
                fields=("customer", "employee"),
                condition=Q(is_active=True),
                name="customer_assignment_active_unique",
            ),
        ]
        indexes = [
            models.Index(
                fields=("employee", "is_active", "customer"),
                name="cust_assign_emp_active_idx",
            ),
            models.Index(
                fields=("customer", "is_active", "employee"),
                name="cust_assign_cust_active_idx",
            ),
        ]

    def __str__(self):
        return f"{self.customer} -> {self.employee}"
