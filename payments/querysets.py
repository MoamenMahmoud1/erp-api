from django.db import models

from services.organization_scope import filter_by_actor_scope


class PaymentTransactionQuerySet(models.QuerySet):
    def visible_to(self, user):
        return filter_by_actor_scope(self, user=user, owner_field="collected_by_id")

    def with_payment_data(self):
        return self.select_related("customer", "collected_by").prefetch_related("allocations__invoice", "refunds")
