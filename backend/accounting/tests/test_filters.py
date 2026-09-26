from datetime import date

from django.test import TestCase

from accounting.api.filters import JournalEntryFilter
from accounting.models import JournalEntry
from accounts.models import CustomUserModel
from organization.models import Company


class JournalEntryFilterTests(TestCase):
    def setUp(self):
        self.company = Company.objects.create(name="Journal Filter Company")
        self.alice = CustomUserModel.objects.create_user(
            username="alice",
            first_name="Alice",
            last_name="Cashier",
            email="alice@example.com",
            password="StrongPass123!",
        )
        self.bob = CustomUserModel.objects.create_user(
            username="bob",
            first_name="Bob",
            last_name="Manager",
            email="bob@example.com",
            password="StrongPass123!",
        )
        self.old = JournalEntry.objects.create(
            company=self.company,
            number=1,
            entry_date=date(2026, 9, 1),
            description="Old sale",
            source_type="invoice.sale",
            source_id=1,
            status=JournalEntry.Status.POSTED,
            created_by=self.alice,
            posted_by=self.bob,
        )
        self.recent = JournalEntry.objects.create(
            company=self.company,
            number=2,
            entry_date=date(2026, 9, 20),
            description="Recent manual entry",
            source_type="",
            source_id=None,
            status=JournalEntry.Status.DRAFT,
            created_by=self.bob,
        )

    def base_queryset(self):
        return JournalEntry.objects.filter(company=self.company)

    def test_filters_by_date_status_actor_and_manual_source(self):
        filtered = JournalEntryFilter(
            {
                "entry_date_from": "2026-09-10",
                "status": "draft",
                "created_by_name": "Bob",
                "source_type": "manual",
            },
            queryset=self.base_queryset(),
        ).qs
        self.assertEqual(list(filtered.values_list("pk", flat=True)), [self.recent.pk])

        filtered = JournalEntryFilter(
            {
                "entry_date_to": "2026-09-10",
                "posted_by_name": "Bob",
            },
            queryset=self.base_queryset(),
        ).qs
        self.assertEqual(list(filtered.values_list("pk", flat=True)), [self.old.pk])
