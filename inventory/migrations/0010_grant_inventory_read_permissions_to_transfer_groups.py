from django.db import migrations


def noop(apps, schema_editor):
    # Permission rows and content types are finalized by Django's post_migrate
    # lifecycle. The corresponding group grants are applied by inventory's
    # post_migrate signal after all migrations complete.
    return None


class Migration(migrations.Migration):
    dependencies = [
        ("inventory", "0009_stock_valuation"),
    ]

    operations = [
        migrations.RunPython(noop, noop),
    ]
