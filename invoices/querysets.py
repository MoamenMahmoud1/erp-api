from django.db import models

from services.organization_scope import filter_by_actor_scope


class InvoiceQuerySet(models.QuerySet):
    def with_invoice_data(self):
        return self.select_related("customer", "created_by", "coupon", "site").prefetch_related("items__product")

    def visible_to(self, user):
        return filter_by_actor_scope(self, user=user, owner_field="created_by_id", site_field="site_id")

    def drafts(self):
        from invoices.models import Invoice
        return self.filter(status=Invoice.Status.DRAFT)
