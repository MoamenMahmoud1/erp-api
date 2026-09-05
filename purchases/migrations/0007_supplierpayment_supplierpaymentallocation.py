from decimal import Decimal

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import migrations, models
from django.db.models import Q

import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("purchases", "0006_alter_purchasereturnitem_unit_price"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="SupplierPayment",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("cash_amount", models.DecimalField(decimal_places=2, max_digits=12, validators=[MinValueValidator(Decimal("0"))])),
                ("transfer_amount", models.DecimalField(decimal_places=2, max_digits=12, validators=[MinValueValidator(Decimal("0"))])),
                ("reference", models.CharField(blank=True, max_length=100)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("paid_by", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="supplier_payments_made", to=settings.AUTH_USER_MODEL)),
                ("supplier", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="supplier_payments", to="suppliers.supplier")),
            ],
            options={
                "ordering": ("-created_at",),
                "constraints": [
                    models.CheckConstraint(condition=Q(cash_amount__gte=Decimal("0")), name="supplier_payment_cash_non_negative"),
                    models.CheckConstraint(condition=Q(transfer_amount__gte=Decimal("0")), name="supplier_payment_transfer_non_negative"),
                    models.CheckConstraint(condition=Q(cash_amount__gt=Decimal("0")) | Q(transfer_amount__gt=Decimal("0")), name="supplier_payment_amount_positive"),
                ],
                "indexes": [models.Index(fields=("supplier", "created_at"), name="supplier_payment_supplier_created_idx")],
            },
        ),
        migrations.CreateModel(
            name="SupplierPaymentAllocation",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("cash_amount", models.DecimalField(decimal_places=2, max_digits=12, validators=[MinValueValidator(Decimal("0"))])),
                ("transfer_amount", models.DecimalField(decimal_places=2, max_digits=12, validators=[MinValueValidator(Decimal("0"))])),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("payment", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="allocations", to="purchases.supplierpayment")),
                ("purchase", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="supplier_payment_allocations", to="purchases.purchase")),
            ],
            options={
                "ordering": ("created_at", "id"),
                "constraints": [
                    models.UniqueConstraint(fields=("payment", "purchase"), name="supplier_payment_alloc_payment_purchase_unique"),
                    models.CheckConstraint(condition=Q(cash_amount__gte=Decimal("0")), name="supplier_payment_alloc_cash_non_negative"),
                    models.CheckConstraint(condition=Q(transfer_amount__gte=Decimal("0")), name="supplier_payment_alloc_transfer_non_negative"),
                    models.CheckConstraint(condition=Q(cash_amount__gt=Decimal("0")) | Q(transfer_amount__gt=Decimal("0")), name="supplier_payment_alloc_amount_positive"),
                ],
            },
        ),
    ]
