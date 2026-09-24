from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("invoices", "0003_hot_path_indexes"),
    ]

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
                default="draft",
                max_length=20,
            ),
        ),
    ]
