import django_filters
from django.db.models import Q

from accounting.models import Expense, JournalEntry


class JournalEntryFilter(django_filters.FilterSet):
    entry_date_from = django_filters.DateFilter(field_name="entry_date", lookup_expr="gte")
    entry_date_to = django_filters.DateFilter(field_name="entry_date", lookup_expr="lte")
    created_by_name = django_filters.CharFilter(method="filter_created_by_name")
    posted_by_name = django_filters.CharFilter(method="filter_posted_by_name")
    source_type = django_filters.CharFilter(method="filter_source_type")

    class Meta:
        model = JournalEntry
        fields = (
            "status",
            "entry_date_from",
            "entry_date_to",
            "created_by_name",
            "posted_by_name",
            "source_type",
        )

    @staticmethod
    def _filter_user_name(queryset, value, field):
        value = value.strip()
        if not value:
            return queryset
        lookup = {
            f"{field}__username__icontains": value,
            f"{field}__email__icontains": value,
            f"{field}__first_name__icontains": value,
            f"{field}__last_name__icontains": value,
        }
        query = Q(**lookup)
        for key in list(lookup)[1:]:
            query |= Q(**{key: value})
        return queryset.filter(query)

    def filter_created_by_name(self, queryset, name, value):
        return self._filter_user_name(queryset, value, "created_by")

    def filter_posted_by_name(self, queryset, name, value):
        return self._filter_user_name(queryset, value, "posted_by")

    def filter_source_type(self, queryset, name, value):
        value = value.strip()
        if value == "manual":
            return queryset.filter(source_type="")
        return queryset.filter(source_type=value)


class ExpenseFilter(django_filters.FilterSet):
    expense_date_from = django_filters.DateFilter(field_name="expense_date", lookup_expr="gte")
    expense_date_to = django_filters.DateFilter(field_name="expense_date", lookup_expr="lte")
    created_by_name = django_filters.CharFilter(method="filter_created_by_name")

    class Meta:
        model = Expense
        fields = (
            "expense_account",
            "payment_account",
            "expense_date",
            "expense_date_from",
            "expense_date_to",
            "created_by_name",
        )

    def filter_created_by_name(self, queryset, name, value):
        value = value.strip()
        if not value:
            return queryset
        return queryset.filter(
            Q(created_by__username__icontains=value)
            | Q(created_by__email__icontains=value)
            | Q(created_by__first_name__icontains=value)
            | Q(created_by__last_name__icontains=value)
        )
