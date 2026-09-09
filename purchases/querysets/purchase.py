from django.db import models

from services.organization_scope import filter_by_actor_scope


class PurchaseQuerySet(models.QuerySet):
    def with_purchase_data(self):
        return self.select_related("supplier", "created_by", "site").prefetch_related("items__product")

    def visible_to(self, user):
        return filter_by_actor_scope(self, user=user, owner_field="created_by_id", site_field="site_id")
