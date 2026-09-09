from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0012_role_scope_least_privilege"),
        ("invoices", "0010_invoice_site"),
        ("organization", "0005_company_metrics_counters"),
    ]

    operations = [
        migrations.AddField(
            model_name="invoice",
            name="shift",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="invoices", to="accounts.employeeshift"),
        ),
        migrations.AddField(
            model_name="invoicereturn",
            name="site",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="invoice_returns", to="organization.site"),
        ),
        migrations.AddField(
            model_name="invoicereturn",
            name="shift",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="invoice_returns", to="accounts.employeeshift"),
        ),
        migrations.AddIndex(
            model_name="invoice",
            index=models.Index(fields=("shift", "created_at"), name="invoice_shift_created_idx"),
        ),
        migrations.AddIndex(
            model_name="invoicereturn",
            index=models.Index(fields=("site", "created_at"), name="invoice_return_site_created_idx"),
        ),
        migrations.AddIndex(
            model_name="invoicereturn",
            index=models.Index(fields=("shift", "created_at"), name="invoice_return_shift_created_idx"),
        ),
    ]
