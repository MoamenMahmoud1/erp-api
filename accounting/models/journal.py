from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import Q


class JournalEntry(models.Model):
    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        POSTED = "posted", "Posted"

    company = models.ForeignKey("organization.Company", on_delete=models.PROTECT, related_name="journal_entries")
    number = models.PositiveBigIntegerField()
    entry_date = models.DateField()
    description = models.CharField(max_length=500, blank=True)
    reference = models.CharField(max_length=120, blank=True)
    source_type = models.CharField(max_length=80, blank=True)
    source_id = models.PositiveBigIntegerField(null=True, blank=True)
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.DRAFT, db_index=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="created_journal_entries")
    posted_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.PROTECT, related_name="posted_journal_entries")
    posted_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-entry_date", "-number")
        constraints = [
            models.UniqueConstraint(fields=("company", "number"), name="journal_entry_company_number_unique"),
            models.UniqueConstraint(fields=("company", "source_type", "source_id"), name="journal_entry_company_source_unique"),
        ]
        indexes = [
            models.Index(fields=("company", "entry_date"), name="journal_company_date_idx"),
            models.Index(fields=("company", "status"), name="journal_company_status_idx"),
            models.Index(fields=("company", "source_type", "source_id"), name="journal_source_lookup_idx"),
        ]
        permissions = [
            ("post_journal_entry", "Can post journal entries"),
            ("view_general_ledger", "Can view the general ledger"),
            ("view_trial_balance", "Can view the trial balance"),
        ]

    def __str__(self):
        return f"JE-{self.number:06d}"


class JournalLine(models.Model):
    entry = models.ForeignKey(JournalEntry, on_delete=models.CASCADE, related_name="lines")
    account = models.ForeignKey("accounting.Account", on_delete=models.PROTECT, related_name="journal_lines")
    description = models.CharField(max_length=300, blank=True)
    debit = models.DecimalField(max_digits=14, decimal_places=2, default=0, validators=[MinValueValidator(0)])
    credit = models.DecimalField(max_digits=14, decimal_places=2, default=0, validators=[MinValueValidator(0)])

    class Meta:
        ordering = ("id",)
        constraints = [
            models.CheckConstraint(
                condition=(Q(debit__gt=0) & Q(credit=0)) | (Q(credit__gt=0) & Q(debit=0)),
                name="journal_line_exactly_one_side",
            ),
        ]
        indexes = [models.Index(fields=("account", "entry"), name="journal_line_account_entry_idx")]

    @property
    def amount(self):
        return self.debit if self.debit else self.credit

    def __str__(self):
        return f"{self.entry_id}:{self.account_id}"
