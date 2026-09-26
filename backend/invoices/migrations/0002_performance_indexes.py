from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("invoices", "0001_initial"),
    ]

    operations = [
        migrations.AddIndex(
            model_name="invoiceitem",
            index=models.Index(
                fields=("product", "invoice"),
                name="invitem_product_invoice_idx",
            ),
        ),
    ]
