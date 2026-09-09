from django.db import migrations, models
from django.db.models import Q


def backfill_location_sites(apps, schema_editor):
    StockLocation = apps.get_model("inventory", "StockLocation")
    Employee = apps.get_model("accounts", "Employee")
    Site = apps.get_model("organization", "Site")

    site_by_user = dict(Employee.objects.exclude(work_site_id=None).values_list("user_id", "work_site_id"))
    fallback_site_id = Site.objects.order_by("id").values_list("id", flat=True).first()

    batch = []
    for location in StockLocation.objects.filter(site_id=None).iterator():
        site_id = site_by_user.get(location.employee_id) or fallback_site_id
        if site_id:
            location.site_id = site_id
            batch.append(location)
        if len(batch) >= 500:
            StockLocation.objects.bulk_update(batch, ["site"])
            batch.clear()
    if batch:
        StockLocation.objects.bulk_update(batch, ["site"])


class Migration(migrations.Migration):
    dependencies = [
        ("inventory", "0010_grant_inventory_read_permissions_to_transfer_groups"),
        ("accounts", "0010_employee_department_employee_work_site"),
        ("organization", "0005_company_metrics_counters"),
    ]

    operations = [
        migrations.AddField(
            model_name="stocklocation",
            name="site",
            field=models.ForeignKey(blank=True, null=True, on_delete=models.deletion.PROTECT, related_name="stock_locations", to="organization.site"),
        ),
        migrations.RunPython(backfill_location_sites, migrations.RunPython.noop),
        migrations.RemoveConstraint(
            model_name="stocklocation",
            name="inventory_one_active_main_warehouse",
        ),
        migrations.AddConstraint(
            model_name="stocklocation",
            constraint=models.UniqueConstraint(condition=Q(is_active=True, location_type="MAIN_WAREHOUSE", site__isnull=False), fields=("site",), name="inventory_one_active_main_warehouse_per_site"),
        ),
        migrations.AddConstraint(
            model_name="stocklocation",
            constraint=models.UniqueConstraint(condition=Q(is_active=True, location_type="MAIN_WAREHOUSE", site__isnull=True), fields=("location_type",), name="inventory_one_legacy_main_warehouse"),
        ),
    ]
