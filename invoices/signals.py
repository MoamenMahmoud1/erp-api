from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from invoices.models import Invoice
from organization.services.metrics import increment_company_counter


@receiver(post_save, sender=Invoice)
def sync_invoice_counter_on_save(sender, instance, created, **kwargs):
    if created:
        increment_company_counter("invoice")


@receiver(post_delete, sender=Invoice)
def sync_invoice_counter_on_delete(sender, instance, **kwargs):
    increment_company_counter("invoice", delta=-1)
