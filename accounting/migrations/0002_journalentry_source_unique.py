from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("accounting", "0001_initial")]

    operations = [
        migrations.AddConstraint(
            model_name="journalentry",
            constraint=models.UniqueConstraint(
                fields=("company", "source_type", "source_id"),
                name="journal_entry_company_source_unique",
            ),
        ),
        migrations.AddIndex(
            model_name="journalentry",
            index=models.Index(
                fields=("company", "source_type", "source_id"),
                name="journal_source_lookup_idx",
            ),
        ),
    ]
