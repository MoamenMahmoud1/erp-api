from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("invoices", "0011_invoice_shift_and_return_site_shift"),
    ]

    operations = [
        migrations.RenameIndex(
            model_name="invoicereturn",
            new_name="iret_site_created_idx",
            old_name="invoice_return_site_created_idx",
        ),
        migrations.RenameIndex(
            model_name="invoicereturn",
            new_name="iret_shift_created_idx",
            old_name="invoice_return_shift_created_idx",
        ),
    ]
