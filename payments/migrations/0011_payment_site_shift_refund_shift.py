from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0012_role_scope_least_privilege"),
        ("payments", "0010_payment_integrity"),
        ("organization", "0005_company_metrics_counters"),
    ]

    operations = [
        migrations.AddField(
            model_name="paymenttransaction",
            name="site",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="payment_transactions", to="organization.site"),
        ),
        migrations.AddField(
            model_name="paymenttransaction",
            name="shift",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="payment_transactions", to="accounts.employeeshift"),
        ),
        migrations.AddField(
            model_name="paymentrefund",
            name="site",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="payment_refunds", to="organization.site"),
        ),
        migrations.AddField(
            model_name="paymentrefund",
            name="shift",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="payment_refunds", to="accounts.employeeshift"),
        ),
        migrations.AddIndex(model_name="paymenttransaction", index=models.Index(fields=("site", "created_at"), name="pay_tx_site_created_idx")),
        migrations.AddIndex(model_name="paymenttransaction", index=models.Index(fields=("shift", "created_at"), name="pay_tx_shift_created_idx")),
        migrations.AddIndex(model_name="paymentrefund", index=models.Index(fields=("site", "created_at"), name="pay_refund_site_created_idx")),
        migrations.AddIndex(model_name="paymentrefund", index=models.Index(fields=("shift", "created_at"), name="pay_refund_shift_created_idx")),
    ]
