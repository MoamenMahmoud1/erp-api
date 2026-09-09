from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0010_employee_department_employee_work_site"),
        ("inventory", "0011_stocklocation_site"),
        ("organization", "0005_company_metrics_counters"),
    ]

    operations = [
        migrations.AddField(
            model_name="role",
            name="scope",
            field=models.CharField(
                choices=[("company", "Company"), ("branch", "Branch"), ("site", "Site")],
                db_index=True,
                default="company",
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name="role",
            name="requires_shift",
            field=models.BooleanField(default=False),
        ),
        migrations.CreateModel(
            name="EmployeeShift",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("business_date", models.DateField()),
                ("status", models.CharField(choices=[("open", "Open"), ("closed", "Closed")], db_index=True, default="open", max_length=10)),
                ("opened_at", models.DateTimeField(auto_now_add=True)),
                ("closed_at", models.DateTimeField(blank=True, null=True)),
                ("opening_cash", models.DecimalField(decimal_places=2, default=0, max_digits=14)),
                ("closing_cash", models.DecimalField(blank=True, decimal_places=2, max_digits=14, null=True)),
                ("closing_transfer", models.DecimalField(blank=True, decimal_places=2, max_digits=14, null=True)),
                ("closing_notes", models.CharField(blank=True, max_length=500)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("employee", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="shifts", to="accounts.employee")),
                ("site", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="employee_shifts", to="organization.site")),
                ("vehicle", models.ForeignKey(blank=True, limit_choices_to={"location_type": "SALES_VEHICLE"}, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="employee_shifts", to="inventory.stocklocation")),
            ],
            options={
                "ordering": ("-business_date", "-opened_at"),
                "permissions": [("start_employee_shift", "Can start an employee shift"), ("close_employee_shift", "Can close an employee shift"), ("view_all_employee_shifts", "Can view all employee shifts")],
            },
        ),
        migrations.AddConstraint(
            model_name="employeeshift",
            constraint=models.UniqueConstraint(fields=("employee", "business_date"), name="accounts_employee_shift_employee_date_unique"),
        ),
        migrations.AddConstraint(
            model_name="employeeshift",
            constraint=models.UniqueConstraint(condition=models.Q(status="open"), fields=("employee",), name="accounts_one_open_shift_per_employee"),
        ),
        migrations.AddConstraint(
            model_name="employeeshift",
            constraint=models.CheckConstraint(
                condition=(
                    models.Q(status="open", closed_at__isnull=True, closing_cash__isnull=True, closing_transfer__isnull=True)
                    | models.Q(status="closed", closed_at__isnull=False, closing_cash__isnull=False, closing_transfer__isnull=False)
                ),
                name="accounts_employee_shift_status_fields_consistent",
            ),
        ),
        migrations.AddConstraint(
            model_name="employeeshift",
            constraint=models.CheckConstraint(condition=models.Q(opening_cash__gte=0), name="accounts_employee_shift_opening_cash_non_negative"),
        ),
        migrations.AddConstraint(
            model_name="employeeshift",
            constraint=models.CheckConstraint(condition=models.Q(closing_cash__isnull=True) | models.Q(closing_cash__gte=0), name="accounts_employee_shift_closing_cash_non_negative"),
        ),
        migrations.AddConstraint(
            model_name="employeeshift",
            constraint=models.CheckConstraint(condition=models.Q(closing_transfer__isnull=True) | models.Q(closing_transfer__gte=0), name="accounts_employee_shift_closing_transfer_non_negative"),
        ),
    ]
