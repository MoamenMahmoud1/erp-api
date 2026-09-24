from django.db import models
from django.db.models import Exists, OuterRef

from accounting.models import JournalEntry
from services.organization_scope import filter_by_actor_scope


class PaymentTransactionQuerySet(models.QuerySet):
    def visible_to(self, user):
        return filter_by_actor_scope(self, user=user, owner_field="collected_by_id", site_field="site_id")

    def with_payment_data(self):
        approved_transfer = JournalEntry.objects.filter(
            source_type="payment.transfer.approval",
            source_id=OuterRef("pk"),
            status=JournalEntry.Status.POSTED,
        )
        return (
            self.annotate(_transfer_approved=Exists(approved_transfer))
            .select_related("customer", "collected_by", "site", "shift")
            .prefetch_related("allocations__invoice", "refunds")
        )
