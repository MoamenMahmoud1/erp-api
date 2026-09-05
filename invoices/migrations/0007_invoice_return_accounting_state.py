from decimal import Decimal

from django.core.validators import MinValueValidator
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("invoices", "0006_invoice_return_permission")]

    operations = [
        migrations.AlterField(
            model_name="invoice",
            name="status",
            field=models.CharField(
                choices=[
                    ("draft", "Draft"),
                    ("confirmed", "Confirmed"),
                    ("cancelled", "Cancelled"),
                    ("paid", "Paid"),
                    ("returned", "Returned"),
                ],
                db_index=True,
                default="draft",
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name="invoicereturn",
            name="refund_amount",
            field=models.DecimalField(
                decimal_places=2,
                default=Decimal("0"),
                max_digits=12,
                validators=[MinValueValidator(Decimal("0"))],
            ),
        ),
        migrations.AddConstraint(
            model_name="invoicereturn",
            constraint=models.CheckConstraint(
                condition=models.Q(refund_amount__gte=Decimal("0")),
                name="invoice_return_refund_amount_non_negative",
            ),
        ),
    ]
