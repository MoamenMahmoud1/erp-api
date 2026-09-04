from django.db import models


class SupplierQuerySet(models.QuerySet):
    def active(self):
        return self.filter(is_active=True)

    def for_list(self):
        return self.only(
            "id",
            "name",
            "phone",
            "email",
            "is_active",
            "created_at",
        )
