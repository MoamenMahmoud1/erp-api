from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("payments", "0008_payment_permissions"),
        ("accounts", "0010_employee_department_employee_work_site"),
    ]

    operations = [
        migrations.AlterField(
            model_name="idempotencykey",
            name="path",
            field=models.CharField(max_length=500),
        ),
        migrations.AlterField(
            model_name="idempotencykey",
            name="request_signature",
            field=models.CharField(max_length=64),
        ),
        migrations.AlterField(
            model_name="paymenttransaction",
            name="collected_by",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="payment_collections",
                to="accounts.user",
            ),
        ),
    ]
