from django.db import migrations, models


def backfill_purchase_sites(apps, schema_editor):
    Purchase = apps.get_model("purchases", "Purchase")
    Employee = apps.get_model("accounts", "Employee")
    site_by_user = dict(Employee.objects.exclude(work_site_id=None).values_list("user_id", "work_site_id"))
    batch = []
    for purchase in Purchase.objects.filter(site_id=None).iterator():
        site_id = site_by_user.get(purchase.created_by_id)
        if site_id:
            purchase.site_id = site_id
            batch.append(purchase)
        if len(batch) >= 500:
            Purchase.objects.bulk_update(batch, ["site"])
            batch.clear()
    if batch:
        Purchase.objects.bulk_update(batch, ["site"])


class Migration(migrations.Migration):
    dependencies = [
        ("purchases", "0009_rename_supplier_payment_index"),
        ("accounts", "0010_employee_department_employee_work_site"),
        ("organization", "0005_company_metrics_counters"),
    ]

    operations = [
        migrations.AddField(
            model_name="purchase",
            name="site",
            field=models.ForeignKey(blank=True, null=True, on_delete=models.deletion.PROTECT, related_name="purchases", to="organization.site"),
        ),
        migrations.RunPython(backfill_purchase_sites, migrations.RunPython.noop),
        migrations.AddIndex(
            model_name="purchase",
            index=models.Index(fields=["site", "created_at"], name="purchase_site_created_idx"),
        ),
    ]
