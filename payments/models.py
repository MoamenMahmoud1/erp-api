from decimal import Decimal

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import Q

from common.money import quantize_money
from payments.querysets import PaymentTransactionQuerySet


class PaymentTransaction(models.Model):
    customer = models.ForeignKey("customers.Customer", on_delete=models.PROTECT, related_name="payment_transactions")
    site = models.ForeignKey("organization.Site", on_delete=models.PROTECT, null=True, blank=True, related_name="payment_transactions")
    shift = models.ForeignKey("accounts.EmployeeShift", on_delete=models.PROTECT, null=True, blank=True, related_name="payment_transactions")
    collected_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="payment_collections", null=True, blank=True)
    cash_amount = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(Decimal("0"))])
    transfer_amount = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(Decimal("0"))])
    created_at = models.DateTimeField(auto_now_add=True)
    objects = PaymentTransactionQuerySet.as_manager()

    class Meta:
        ordering = ("-created_at",)
        indexes = [
            models.Index(fields=("customer", "created_at"), name="pay_tx_cust_created_idx"),
            models.Index(fields=("site", "created_at"), name="pay_tx_site_created_idx"),
            models.Index(fields=("shift", "created_at"), name="pay_tx_shift_created_idx"),
        ]
        constraints = [
            models.CheckConstraint(condition=Q(cash_amount__gte=Decimal("0")), name="payment_tx_cash_non_negative"),
            models.CheckConstraint(condition=Q(transfer_amount__gte=Decimal("0")), name="payment_tx_transfer_non_negative"),
            models.CheckConstraint(condition=Q(cash_amount__gt=Decimal("0")) | Q(transfer_amount__gt=Decimal("0")), name="payment_tx_amount_positive"),
        ]
        permissions = [
            ("process_collection", "Can process a payment collection"),
            ("refund_payment", "Can refund a payment"),
        ]

    @property
    def total_amount(self) -> Decimal:
        return quantize_money(self.cash_amount + self.transfer_amount)

    @property
    def refunded_amount(self) -> Decimal:
        return quantize_money(sum((item.total_amount for item in self.refunds.all()), Decimal("0")))

    @property
    def refundable_amount(self) -> Decimal:
        return quantize_money(self.total_amount - self.refunded_amount)

    def __str__(self):
        return f"Tx {self.pk} ({self.customer_id})"


class PaymentAllocation(models.Model):
    transaction = models.ForeignKey(PaymentTransaction, on_delete=models.CASCADE, related_name="allocations")
    invoice = models.ForeignKey("invoices.Invoice", on_delete=models.PROTECT, related_name="payment_allocations")
    cash_amount = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(Decimal("0"))])
    transfer_amount = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(Decimal("0"))])
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("created_at",)
        constraints = [
            models.UniqueConstraint(fields=("transaction", "invoice"), name="payment_alloc_unique_tx_invoice"),
            models.CheckConstraint(condition=Q(cash_amount__gte=Decimal("0")), name="payment_alloc_cash_non_negative"),
            models.CheckConstraint(condition=Q(transfer_amount__gte=Decimal("0")), name="payment_alloc_transfer_non_negative"),
            models.CheckConstraint(condition=Q(cash_amount__gt=Decimal("0")) | Q(transfer_amount__gt=Decimal("0")), name="payment_alloc_amount_positive"),
        ]

    @property
    def total_amount(self) -> Decimal:
        return quantize_money(self.cash_amount + self.transfer_amount)

    @property
    def refunded_amount(self) -> Decimal:
        return quantize_money(sum((item.total_amount for item in self.refunds.all()), Decimal("0")))

    @property
    def refundable_amount(self) -> Decimal:
        return quantize_money(self.total_amount - self.refunded_amount)

    def __str__(self):
        return f"Alloc {self.pk} -> invoice {self.invoice_id}"


class PaymentRefund(models.Model):
    transaction = models.ForeignKey(PaymentTransaction, on_delete=models.PROTECT, related_name="refunds")
    invoice = models.ForeignKey("invoices.Invoice", on_delete=models.PROTECT, related_name="payment_refunds")
    allocation = models.ForeignKey(PaymentAllocation, on_delete=models.PROTECT, related_name="refunds")
    site = models.ForeignKey("organization.Site", on_delete=models.PROTECT, null=True, blank=True, related_name="payment_refunds")
    shift = models.ForeignKey("accounts.EmployeeShift", on_delete=models.PROTECT, null=True, blank=True, related_name="payment_refunds")
    cash_amount = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(Decimal("0"))])
    transfer_amount = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(Decimal("0"))])
    reason = models.CharField(max_length=255, blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="created_payment_refunds")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("created_at",)
        indexes = [
            models.Index(fields=("site", "created_at"), name="pay_refund_site_created_idx"),
            models.Index(fields=("shift", "created_at"), name="pay_refund_shift_created_idx"),
        ]
        constraints = [
            models.CheckConstraint(condition=Q(cash_amount__gte=Decimal("0")), name="payment_refund_cash_non_negative"),
            models.CheckConstraint(condition=Q(transfer_amount__gte=Decimal("0")), name="payment_refund_transfer_non_negative"),
            models.CheckConstraint(condition=Q(cash_amount__gt=Decimal("0")) | Q(transfer_amount__gt=Decimal("0")), name="payment_refund_amount_positive"),
        ]

    @property
    def total_amount(self) -> Decimal:
        return quantize_money(self.cash_amount + self.transfer_amount)


class IdempotencyKey(models.Model):
    key = models.CharField(max_length=128, db_index=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="idempotency_keys")
    path = models.CharField(max_length=500)
    request_signature = models.CharField(max_length=64)
    response_status = models.PositiveSmallIntegerField()
    response_body = models.JSONField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=("key", "user", "path"), name="idempotency_unique_key_user_path"),
            models.CheckConstraint(condition=Q(response_status=0) | Q(response_status__gte=100, response_status__lte=599), name="idempotency_response_status_valid"),
        ]
        indexes = [models.Index(fields=("user", "path", "key"), name="idempotency_lookup_idx")]

    def __str__(self):
        return f"Idempotency {self.key} ({self.user_id})"
