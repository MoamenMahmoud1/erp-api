from django.db import migrations, models


def backfill_invoice_sites(apps, schema_editor):
    Invoice = apps.get_model("invoices", "Invoice")
    Employee = apps.get_model("accounts", "Employee")
    site_by_user = dict(Employee.objects.exclude(work_site_id=None).values_list("user_id", "work_site_id"))
    batch = []
    for invoice in Invoice.objects.filter(site_id=None).iterator():
        site_id = site_by_user.get(invoice.created_by_id)
        if site_id:
            invoice.site_id = site_id
            batch.append(invoice)
        if len(batch) >= 500:
            Invoice.objects.bulk_update(batch, ["site"])
            batch.clear()
    if batch:
        Invoice.objects.bulk_update(batch, ["site"])


class Migration(migrations.Migration):
    dependencies = [
        ("invoices", "0009_invoiceitem_cost_price"),
        ("organization", "0005_company_metrics_counters"),
        ("accounts", "0010_employee_department_employee_work_site"),
    ]

    operations = [
        migrations.AddField(
            model_name="invoice",
            name="site",
            field=models.ForeignKey(blank=True, null=True, on_delete=models.deletion.PROTECT, related_name="invoices", to="organization.site"),
        ),
        migrations.RunPython(backfill_invoice_sites, migrations.RunPython.noop),
        migrations.AddIndex(
            model_name="invoice",
            index=models.Index(fields=["site", "created_at"], name="invoice_site_created_idx"),
        ),
    ]
