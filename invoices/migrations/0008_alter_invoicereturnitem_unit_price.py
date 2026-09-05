from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("invoices", "0007_invoice_return_accounting_state")]

    operations = [
        migrations.AlterField(
            model_name="invoicereturnitem",
            name="unit_price",
            field=models.DecimalField(decimal_places=2, max_digits=12),
        ),
    ]
