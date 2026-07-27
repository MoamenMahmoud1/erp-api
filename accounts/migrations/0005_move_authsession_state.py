from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0004_authsession"),
    ]
    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[],
            state_operations=[
                migrations.DeleteModel(name="AuthSession"),
            ],
        ),
    ]
