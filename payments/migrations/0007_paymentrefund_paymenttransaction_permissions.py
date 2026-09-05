from decimal import Decimal

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0010_employee_department_employee_work_site"),
        ("invoices", "0005_invoicereturn_invoicereturnitem"),
        ("payments", "0006_paymenttransaction_collected_by_and_more"),
    ]

    operations = [
        migrations.CreateModel(
            name="PaymentRefund",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("cash_amount", models.DecimalField(decimal_places=2, max_digits=12, validators=[MinValueValidator(Decimal("0"))])),
                ("transfer_amount", models.DecimalField(decimal_places=2, max_digits=12, validators=[MinValueValidator(Decimal("0"))])),
                ("reason", models.CharField(blank=True, max_length=255)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("allocation", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="refunds", to="payments.paymentallocation")),
                ("created_by", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="created_payment_refunds", to=settings.AUTH_USER_MODEL)),
                ("invoice", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="payment_refunds", to="invoices.invoice")),
                ("transaction", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="refunds", to="payments.paymenttransaction")),
            ],
            options={
                "ordering": ("created_at",),
                "constraints": [
                    models.CheckConstraint(condition=models.Q(cash_amount__gte=Decimal("0")), name="payment_refund_cash_non_negative"),
                    models.CheckConstraint(condition=models.Q(transfer_amount__gte=Decimal("0")), name="payment_refund_transfer_non_negative"),
                ],
            },
        ),
    ]
