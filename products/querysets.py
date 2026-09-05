from django.db import models


class ProductQuerySet(models.QuerySet):
    def active(self):
        return self.filter(is_active=True)

    def with_stock_stats(self):
        from django.db.models import OuterRef, Subquery, Sum, Value
        from django.db.models.functions import Coalesce
        from invoices.models import Invoice, InvoiceItem

        sold = (
            InvoiceItem.objects.filter(
                product=OuterRef("pk"),
                invoice__status__in=(Invoice.Status.CONFIRMED, Invoice.Status.PAID),
            )
            .values("product")
            .annotate(total=Sum("quantity"))
            .values("total")
        )
        stock = (
            self.model.objects.filter(pk=OuterRef("pk"))
            .values("pk")
            .annotate(total=Sum("stock_balances__quantity"))
            .values("total")
        )
        return self.annotate(
            _total_stock=Coalesce(Subquery(stock), Value(0)),
            _sold_quantity=Coalesce(Subquery(sold), Value(0)),
        )
