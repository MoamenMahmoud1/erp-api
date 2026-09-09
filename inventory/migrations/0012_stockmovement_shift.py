from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0012_role_scope_least_privilege"),
        ("inventory", "0011_stocklocation_site"),
    ]

    operations = [
        migrations.AddField(
            model_name="stockmovement",
            name="shift",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="stock_movements", to="accounts.employeeshift"),
        ),
    ]
