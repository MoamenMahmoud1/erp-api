from decimal import Decimal

from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import Q

from common.money import quantize_money


class PaymentTransaction(models.Model):
    """A single collection received from a customer.

    A transaction is a (cash, transfer) pair that is then allocated across one
    or more of the customer's invoices via ``PaymentAllocation`` rows. The
    backend owns the allocation — the client only reports how much cash and
    transfer was received.

    ``collected_by`` records the authenticated employee/user who performed
    the collection.  It is a durable audit field — never derived from a
    dynamic attribute.
    """

    customer = models.ForeignKey(
        "customers.Customer",
        on_delete=models.PROTECT,
        related_name="payment_transactions",
    )
    collected_by = models.ForeignKey(
        "accounts.CustomUserModel",
        on_delete=models.PROTECT,
        related_name="payment_collections",
        help_text="Authenticated user who performed the collection.",
        null=True,
        blank=True,
    )
    cash_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0"))],
    )
    transfer_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0"))],
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-created_at",)
        indexes = [
            models.Index(
                fields=("customer", "created_at"),
                name="pay_tx_cust_created_idx",
            ),
        ]
        constraints = [
            models.CheckConstraint(
                condition=Q(cash_amount__gte=Decimal("0")),
                name="payment_tx_cash_non_negative",
            ),
            models.CheckConstraint(
                condition=Q(transfer_amount__gte=Decimal("0")),
                name="payment_tx_transfer_non_negative",
            ),
        ]
        permissions = [
            (
                "process_collection",
                "Can process a payment collection",
            ),
        ]

    @property
    def total_amount(self) -> Decimal:
        return quantize_money(self.cash_amount + self.transfer_amount)

    def __str__(self):
        return f"Tx {self.pk} ({self.customer_id})"


class PaymentAllocation(models.Model):
    """Money from one transaction allocated to one invoice.

    ``cash_amount + transfer_amount`` is the portion of the transaction that
    reduces the target invoice's outstanding balance.
    """

    transaction = models.ForeignKey(
        PaymentTransaction,
        on_delete=models.CASCADE,
        related_name="allocations",
    )
    invoice = models.ForeignKey(
        "invoices.Invoice",
        on_delete=models.PROTECT,
        related_name="payment_allocations",
    )
    cash_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0"))],
    )
    transfer_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0"))],
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("created_at",)
        constraints = [
            models.UniqueConstraint(
                fields=("transaction", "invoice"),
                name="payment_alloc_unique_tx_invoice",
            ),
            models.CheckConstraint(
                condition=Q(cash_amount__gte=Decimal("0")),
                name="payment_alloc_cash_non_negative",
            ),
            models.CheckConstraint(
                condition=Q(transfer_amount__gte=Decimal("0")),
                name="payment_alloc_transfer_non_negative",
            ),
        ]

    @property
    def total_amount(self) -> Decimal:
        return quantize_money(self.cash_amount + self.transfer_amount)

    def __str__(self):
        return f"Alloc {self.pk} -> invoice {self.invoice_id}"


class IdempotencyKey(models.Model):
    """DB-backed idempotency for financial write operations.

    A client provides ``Idempotency-Key`` for a collection request.  If the
    same key (scoped to the user and the target endpoint path) is seen again,
    the previously persisted response is returned instead of re-executing the
    service.  This guards against duplicate collections caused by network
    retries.

    Keys are durable in PostgreSQL — they are never solely Redis-backed.
    """

    key = models.CharField(max_length=128, db_index=True)
    user = models.ForeignKey(
        "accounts.CustomUserModel",
        on_delete=models.PROTECT,
        related_name="idempotency_keys",
    )
    path = models.CharField(max_length=500, help_text="Normalized request path.")
    request_signature = models.CharField(
        max_length=64,
        help_text="SHA-256 of the canonical request body.",
    )
    response_status = models.PositiveSmallIntegerField()
    response_body = models.JSONField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("key", "user", "path"),
                name="idempotency_unique_key_user_path",
            ),
        ]
        indexes = [
            models.Index(
                fields=("user", "path", "key"),
                name="idempotency_lookup_idx",
            ),
        ]

    def __str__(self):
        return f"Idempotency {self.key} ({self.user_id})"
