from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("payments", "0008_payment_permissions"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AlterField(
            model_name="idempotencykey",
            name="path",
            field=models.CharField(max_length=500),
        ),
        migrations.AlterField(
            model_name="idempotencykey",
            name="request_signature",
            field=models.CharField(max_length=64),
        ),
        migrations.AlterField(
            model_name="paymenttransaction",
            name="collected_by",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="payment_collections",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
    ]
