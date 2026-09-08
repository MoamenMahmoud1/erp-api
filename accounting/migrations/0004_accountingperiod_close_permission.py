from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("accounting", "0003_expense_accountingperiod"),
    ]

    operations = [
        migrations.AlterModelOptions(
            name="accountingperiod",
            options={
                "ordering": ("-start_date",),
                "permissions": [
                    ("close_accounting_period", "Can close an accounting period"),
                ],
            },
        ),
    ]
