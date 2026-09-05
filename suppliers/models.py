from django.db import models
from .querysets.supplier import SupplierQuerySet

class Supplier(models.Model):
    name = models.CharField(max_length=150)
    phone = models.CharField(max_length=30, blank=True)
    email = models.EmailField(blank=True)
    address = models.CharField(max_length=255, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    objects = SupplierQuerySet.as_manager()

    class Meta:
        ordering = ("name",)

    def __str__(self):
        return self.name