from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0012_role_scope_least_privilege"),
        ("purchases", "0010_purchase_site"),
        ("organization", "0005_company_metrics_counters"),
    ]

    operations = [
        migrations.AddField(
            model_name="purchase",
            name="shift",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="purchases", to="accounts.employeeshift"),
        ),
        migrations.AddField(
            model_name="purchasereturn",
            name="site",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="purchase_returns", to="organization.site"),
        ),
        migrations.AddField(
            model_name="purchasereturn",
            name="shift",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="purchase_returns", to="accounts.employeeshift"),
        ),
        migrations.AddField(
            model_name="supplierpayment",
            name="site",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="supplier_payments", to="organization.site"),
        ),
        migrations.AddField(
            model_name="supplierpayment",
            name="shift",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="supplier_payments", to="accounts.employeeshift"),
        ),
        migrations.AddIndex(model_name="purchase", index=models.Index(fields=("shift", "created_at"), name="purchase_shift_created_idx")),
        migrations.AddIndex(model_name="purchasereturn", index=models.Index(fields=("site", "created_at"), name="purchase_return_site_created_idx")),
        migrations.AddIndex(model_name="purchasereturn", index=models.Index(fields=("shift", "created_at"), name="purchase_return_shift_created_idx")),
        migrations.AddIndex(model_name="supplierpayment", index=models.Index(fields=("site", "created_at"), name="suppay_site_created_idx")),
        migrations.AddIndex(model_name="supplierpayment", index=models.Index(fields=("shift", "created_at"), name="suppay_shift_created_idx")),
    ]
