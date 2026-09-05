from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import migrations, models
import django.db.models.deletion
from decimal import Decimal


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ("organization", "0004_department"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="Account",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("code", models.CharField(max_length=32)),
                ("name", models.CharField(max_length=200)),
                ("account_type", models.CharField(choices=[("asset", "Asset"), ("liability", "Liability"), ("equity", "Equity"), ("revenue", "Revenue"), ("expense", "Expense")], max_length=20)),
                ("is_active", models.BooleanField(db_index=True, default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("company", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="accounts", to="organization.company")),
                ("parent", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="children", to="accounting.account")),
            ],
            options={
                "ordering": ("code",),
                "permissions": [("manage_chart_of_accounts", "Can manage the chart of accounts"), ("view_financial_reports", "Can view financial reports")],
                "constraints": [models.UniqueConstraint(fields=("company", "code"), name="accounting_account_company_code_unique")],
                "indexes": [models.Index(fields=("company", "account_type"), name="acct_company_type_idx")],
            },
        ),
        migrations.CreateModel(
            name="JournalEntry",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("number", models.PositiveBigIntegerField()),
                ("entry_date", models.DateField()),
                ("description", models.CharField(blank=True, max_length=500)),
                ("reference", models.CharField(blank=True, max_length=120)),
                ("source_type", models.CharField(blank=True, max_length=80)),
                ("source_id", models.PositiveBigIntegerField(blank=True, null=True)),
                ("status", models.CharField(choices=[("draft", "Draft"), ("posted", "Posted")], db_index=True, default="draft", max_length=12)),
                ("posted_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("company", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="journal_entries", to="organization.company")),
                ("created_by", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="created_journal_entries", to=settings.AUTH_USER_MODEL)),
                ("posted_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="posted_journal_entries", to=settings.AUTH_USER_MODEL)),
            ],
            options={
                "ordering": ("-entry_date", "-number"),
                "permissions": [("post_journal_entry", "Can post journal entries"), ("view_general_ledger", "Can view the general ledger"), ("view_trial_balance", "Can view the trial balance")],
                "constraints": [models.UniqueConstraint(fields=("company", "number"), name="journal_entry_company_number_unique")],
                "indexes": [models.Index(fields=("company", "entry_date"), name="journal_company_date_idx"), models.Index(fields=("company", "status"), name="journal_company_status_idx")],
            },
        ),
        migrations.CreateModel(
            name="JournalLine",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("description", models.CharField(blank=True, max_length=300)),
                ("debit", models.DecimalField(decimal_places=2, default=0, max_digits=14, validators=[MinValueValidator(Decimal("0"))])),
                ("credit", models.DecimalField(decimal_places=2, default=0, max_digits=14, validators=[MinValueValidator(Decimal("0"))])),
                ("account", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="journal_lines", to="accounting.account")),
                ("entry", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="lines", to="accounting.journalentry")),
            ],
            options={
                "ordering": ("id",),
                "constraints": [models.CheckConstraint(condition=(models.Q(("debit__gt", 0)) & models.Q(("credit", 0))) | (models.Q(("credit__gt", 0)) & models.Q(("debit", 0))), name="journal_line_exactly_one_side")],
                "indexes": [models.Index(fields=("account", "entry"), name="journal_line_account_entry_idx")],
            },
        ),
    ]
