"""Transactional master-data counters and their reconciliation routine."""

from django.db import transaction
from django.db.models import F
from django.utils import timezone

from organization.models import Company

_COUNTER_FIELDS = {
    "product": "product_count",
    "invoice": "invoice_count",
    "customer": "customer_count",
    "supplier": "supplier_count",
}


def increment_company_counter(counter, delta=1):
    """Apply an O(1) counter change using a database-side expression."""
    field = _COUNTER_FIELDS[counter]
    Company.objects.filter(singleton_marker=True).update(
        **{field: F(field) + delta},
    )


def company_master_data_counts():
    """Read dashboard master-data counts without scanning source tables."""
    company = (
        Company.objects.only(
            "product_count",
            "invoice_count",
            "customer_count",
            "supplier_count",
        )
        .get(singleton_marker=True)
    )
    return {
        "products": company.product_count,
        "invoices": company.invoice_count,
        "customers": company.customer_count,
        "suppliers": company.supplier_count,
    }


def reconcile_company_counters():
    """Rebuild counters from authoritative tables and record the check time."""
    from customers.models import Customer
    from invoices.models import Invoice
    from products.models import Product
    from suppliers.models import Supplier

    counts = {
        "product_count": Product.objects.count(),
        "invoice_count": Invoice.objects.count(),
        "customer_count": Customer.objects.count(),
        "supplier_count": Supplier.objects.count(),
    }

    with transaction.atomic():
        company = Company.objects.select_for_update().get(singleton_marker=True)
        for field, value in counts.items():
            setattr(company, field, value)
        company.counters_reconciled_at = timezone.now()
        company.save(
            update_fields=(
                *counts.keys(),
                "counters_reconciled_at",
                "updated_at",
            ),
        )

    return counts
