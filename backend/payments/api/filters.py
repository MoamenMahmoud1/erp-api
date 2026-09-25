import django_filters
from django.db.models import Exists, OuterRef, Q

from accounting.models import JournalEntry
from accounting.services import get_default_company
from payments.models import PaymentTransaction


class PaymentTransactionFilter(django_filters.FilterSet):
    created_date_from = django_filters.DateFilter(field_name="created_at", lookup_expr="date__gte")
    created_date_to = django_filters.DateFilter(field_name="created_at", lookup_expr="date__lte")
    collected_by_name = django_filters.CharFilter(method="filter_collected_by_name")
    transfer_status = django_filters.CharFilter(method="filter_transfer_status")

    class Meta:
        model = PaymentTransaction
        fields = (
            "customer",
            "collected_by",
            "site",
            "created_date_from",
            "created_date_to",
            "collected_by_name",
            "transfer_status",
        )

    def filter_collected_by_name(self, queryset, name, value):
        value = value.strip()
        if not value:
            return queryset
        return queryset.filter(
            Q(collected_by__username__icontains=value)
            | Q(collected_by__email__icontains=value)
            | Q(collected_by__first_name__icontains=value)
            | Q(collected_by__last_name__icontains=value)
        )

    def filter_transfer_status(self, queryset, name, value):
        value = value.strip().lower()
        approval = JournalEntry.objects.filter(
            company=get_default_company(),
            source_type="payment.transfer.approval",
            source_id=OuterRef("pk"),
            status=JournalEntry.Status.POSTED,
        )
        queryset = queryset.annotate(_transfer_accepted=Exists(approval))
        if value == "pending":
            return queryset.filter(transfer_amount__gt=0, _transfer_accepted=False)
        if value == "accepted":
            return queryset.filter(transfer_amount__gt=0, _transfer_accepted=True)
        if value == "not_applicable":
            return queryset.filter(transfer_amount=0)
        return queryset.none()
