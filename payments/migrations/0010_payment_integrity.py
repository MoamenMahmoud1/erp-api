from decimal import Decimal

from django.db import migrations, models
from django.db.models import Q


class Migration(migrations.Migration):
    dependencies = [
        ("payments", "0009_alter_idempotencykey_path_and_more"),
    ]

    operations = [
        migrations.AddConstraint(
            model_name="paymenttransaction",
            constraint=models.CheckConstraint(
                condition=Q(cash_amount__gt=Decimal("0"))
                | Q(transfer_amount__gt=Decimal("0")),
                name="payment_tx_amount_positive",
            ),
        ),
        migrations.AddConstraint(
            model_name="paymentallocation",
            constraint=models.CheckConstraint(
                condition=Q(cash_amount__gt=Decimal("0"))
                | Q(transfer_amount__gt=Decimal("0")),
                name="payment_alloc_amount_positive",
            ),
        ),
        migrations.AddConstraint(
            model_name="paymentrefund",
            constraint=models.CheckConstraint(
                condition=Q(cash_amount__gt=Decimal("0"))
                | Q(transfer_amount__gt=Decimal("0")),
                name="payment_refund_amount_positive",
            ),
        ),
        migrations.AddConstraint(
            model_name="idempotencykey",
            constraint=models.CheckConstraint(
                condition=Q(response_status=0)
                | Q(response_status__gte=100, response_status__lte=599),
                name="idempotency_response_status_valid",
            ),
        ),
    ]
