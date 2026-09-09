from django.db import migrations, models
import django.db.models.deletion
from django.db.models import F, Q


class Migration(migrations.Migration):
    dependencies = [
        ("inventory", "0013_batch_tracking"),
        ("purchases", "0011_purchase_shift_and_payment_site_shift"),
    ]

    operations = [
        migrations.AddField(
            model_name="purchaseitem",
            name="batch_number",
            field=models.CharField(blank=True, max_length=100, null=True),
        ),
        migrations.AddField(
            model_name="purchaseitem",
            name="manufactured_date",
            field=models.DateField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="purchaseitem",
            name="expiry_date",
            field=models.DateField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="purchaseitem",
            name="batch",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="purchase_items", to="inventory.inventorybatch"),
        ),
        migrations.AddConstraint(
            model_name="purchaseitem",
            constraint=models.CheckConstraint(
                condition=Q(expiry_date__isnull=True) | Q(manufactured_date__isnull=True) | Q(expiry_date__gte=F("manufactured_date")),
                name="purchase_item_dates_ordered",
            ),
        ),
    ]
