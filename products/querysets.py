from django.db import models


class ProductQuerySet(models.QuerySet):
    def active(self):
        return self.filter(is_active=True)

    def with_stock_stats(self):
        from django.db.models import ExpressionWrapper, IntegerField, OuterRef, Subquery, Sum, Value
        from django.db.models.functions import Coalesce
        from invoices.models import Invoice, InvoiceItem, InvoiceReturnItem

        sold = (
            InvoiceItem.objects.filter(
                product=OuterRef("pk"),
                invoice__status__in=(Invoice.Status.CONFIRMED, Invoice.Status.PAID, Invoice.Status.RETURNED),
            )
            .values("product")
            .annotate(total=Sum("quantity"))
            .values("total")
        )
        returned = (
            InvoiceReturnItem.objects.filter(invoice_item__product=OuterRef("pk"))
            .values("invoice_item__product")
            .annotate(total=Sum("quantity"))
            .values("total")
        )
        stock = (
            self.model.objects.filter(pk=OuterRef("pk"))
            .values("pk")
            .annotate(total=Sum("stock_balances__quantity"))
            .values("total")
        )
        sold_quantity = ExpressionWrapper(
            Coalesce(Subquery(sold), Value(0)) - Coalesce(Subquery(returned), Value(0)),
            output_field=IntegerField(),
        )
        return self.annotate(
            _total_stock=Coalesce(Subquery(stock), Value(0)),
            _sold_quantity=sold_quantity,
        )
