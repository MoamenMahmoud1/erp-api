import django_filters

from invoices.models import Invoice


class InvoiceFilter(django_filters.FilterSet):
    customer = django_filters.NumberFilter(field_name="customer_id")
    status = django_filters.ChoiceFilter(choices=Invoice.Status.choices)
    created_by = django_filters.NumberFilter(field_name="created_by_id")
    min_total = django_filters.NumberFilter(field_name="total", lookup_expr="gte", method="filter_total")
    max_total = django_filters.NumberFilter(field_name="total", lookup_expr="lte", method="filter_total")

    class Meta:
        model = Invoice
        fields = ("customer", "status", "created_by", "min_total", "max_total")

    def filter_total(self, queryset, name, value):
        # total is a derived property, so total-range filtering must use item sums.
        from django.db.models import DecimalField, ExpressionWrapper, F, Sum
        from django.db.models.functions import Cast

        expression = ExpressionWrapper(
            Sum(F("items__unit_price") * F("items__quantity")),
            output_field=DecimalField(max_digits=12, decimal_places=2),
        )
        lookup = "gte" if name == "min_total" else "lte"
        return queryset.annotate(_gross_total=Cast(expression, DecimalField(max_digits=12, decimal_places=2))).filter(**{f"_gross_total__{lookup}": value})
