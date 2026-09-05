from decimal import Decimal

from django.db import migrations, models
from django.core.validators import MinValueValidator
from django.db.models import Q


class Migration(migrations.Migration):
    dependencies = [("invoices", "0008_alter_invoicereturnitem_unit_price")]

    operations = [
        migrations.AddField(
            model_name="invoiceitem",
            name="cost_price",
            field=models.DecimalField(
                blank=True,
                decimal_places=2,
                max_digits=12,
                null=True,
                validators=[MinValueValidator(Decimal("0"))],
            ),
        ),
        migrations.AddConstraint(
            model_name="invoiceitem",
            constraint=models.CheckConstraint(
                condition=Q(cost_price__gte=Decimal("0")) | Q(cost_price__isnull=True),
                name="invoice_item_cost_price_non_negative",
            ),
        ),
    ]
