from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("invoices", "0002_performance_indexes"),
    ]

    operations = [
        migrations.AddIndex(
            model_name="invoice",
            index=models.Index(fields=("created_at", "id"), name="invoice_created_id_idx"),
        ),
        migrations.AddIndex(
            model_name="invoice",
            index=models.Index(fields=("status", "created_at"), name="invoice_status_created_idx"),
        ),
        migrations.AddIndex(
            model_name="invoicereturn",
            index=models.Index(fields=("created_at", "id"), name="iret_created_id_idx"),
        ),
    ]
