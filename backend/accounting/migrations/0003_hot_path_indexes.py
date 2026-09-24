from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("accounting", "0002_initial"),
    ]

    operations = [
        migrations.AddIndex(
            model_name="journalentry",
            index=models.Index(fields=("company", "reference"), name="journal_company_reference_idx"),
        ),
        migrations.AddIndex(
            model_name="expense",
            index=models.Index(fields=("company", "expense_account", "expense_date"), name="expense_account_date_idx"),
        ),
        migrations.AddIndex(
            model_name="expense",
            index=models.Index(fields=("company", "payment_account", "expense_date"), name="expense_payment_date_idx"),
        ),
    ]
