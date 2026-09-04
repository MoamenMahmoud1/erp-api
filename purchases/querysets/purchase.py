from django.db import models


class PurchaseQuerySet(models.QuerySet):
    def with_purchase_data(self):
        return (
            self.select_related(
                "supplier",
                "created_by",
            )
            .prefetch_related(
                "items__product",
            )
        )

    def visible_to(self, user):
        return self.filter(created_by=user)