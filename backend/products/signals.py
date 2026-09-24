from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from organization.services.metrics import increment_company_counter
from products.models import Product


@receiver(post_save, sender=Product)
def sync_product_counter_on_save(sender, instance, created, **kwargs):
    if created:
        increment_company_counter("product")


@receiver(post_delete, sender=Product)
def sync_product_counter_on_delete(sender, instance, **kwargs):
    increment_company_counter("product", delta=-1)
