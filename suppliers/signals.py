from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from organization.services.metrics import increment_company_counter
from suppliers.models import Supplier


@receiver(post_save, sender=Supplier)
def sync_supplier_counter_on_save(sender, instance, created, **kwargs):
    if created:
        increment_company_counter("supplier")


@receiver(post_delete, sender=Supplier)
def sync_supplier_counter_on_delete(sender, instance, **kwargs):
    increment_company_counter("supplier", delta=-1)
