from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from customers.models import Customer
from organization.services.metrics import increment_company_counter


@receiver(post_save, sender=Customer)
def sync_customer_counter_on_save(sender, instance, created, **kwargs):
    if created:
        increment_company_counter("customer")


@receiver(post_delete, sender=Customer)
def sync_customer_counter_on_delete(sender, instance, **kwargs):
    increment_company_counter("customer", delta=-1)
