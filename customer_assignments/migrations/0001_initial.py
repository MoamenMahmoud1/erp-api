from django.db import migrations, models
import django.db.models.deletion
from django.db.models import Q


class Migration(migrations.Migration):
    initial = True

    operations = [
        migrations.CreateModel(
            name="CustomerAssignment",
            fields=[
                (
                    "id",
                    models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID"),
                ),
                ("is_active", models.BooleanField(db_index=True, default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "customer",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="representative_assignments",
                        to="customers.customer",
                    ),
                ),
                (
                    "employee",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="customer_assignments",
                        to="accounts.employee",
                    ),
                ),
            ],
            options={
                "ordering": ("customer_id", "employee_id"),
                "indexes": [
                    models.Index(
                        fields=["employee", "is_active", "customer"],
                        name="cust_assign_emp_active_idx",
                    ),
                    models.Index(
                        fields=["customer", "is_active", "employee"],
                        name="cust_assign_cust_active_idx",
                    ),
                ],
                "constraints": [
                    models.UniqueConstraint(
                        condition=Q(is_active=True),
                        fields=("customer", "employee"),
                        name="customer_assignment_active_unique",
                    ),
                ],
            },
        ),
    ]
