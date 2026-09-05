from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [("invoices", "0005_invoicereturn_invoicereturnitem")]

    operations = [
        migrations.AlterModelOptions(
            name="invoice",
            options={
                "ordering": ("-created_at",),
                "permissions": [
                    ("confirm_invoice", "Can confirm an invoice"),
                    ("cancel_invoice", "Can cancel an invoice"),
                    ("apply_invoice_coupon", "Can apply a coupon to an invoice"),
                    ("return_invoice", "Can return items from a paid invoice"),
                ],
            },
        ),
    ]
