from decimal import Decimal

from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import Q, Sum

from products.querysets import ProductQuerySet


_INVOICE_SALE_STATUSES = ("confirmed", "paid")


class Product(models.Model):
    name = models.CharField(max_length=200)
    category = models.CharField(max_length=100, default="General", db_index=True)
    purchase_price = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(Decimal("0"))])
    selling_price = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(Decimal("0"))])
    is_active = models.BooleanField(default=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    objects = ProductQuerySet.as_manager()

    class Meta:
        ordering = ("category", "name")
        indexes = [
            models.Index(fields=("name",), name="products_product_name_idx"),
            models.Index(fields=("category", "name"), name="products_product_cat_name_idx"),
        ]
        constraints = [
            models.CheckConstraint(condition=Q(purchase_price__gte=Decimal("0")), name="product_purchase_price_non_negative"),
            models.CheckConstraint(condition=Q(selling_price__gte=Decimal("0")), name="product_selling_price_non_negative"),
        ]

    @property
    def total_stock(self):
        annotated = getattr(self, "_total_stock", None)
        if annotated is not None:
            return annotated
        return self.stock_balances.aggregate(total=Sum("quantity"))["total"] or 0

    @property
    def stock_quantity(self):
        return self.total_stock

    @property
    def sold_quantity(self):
        if hasattr(self, "_sold_quantity"):
            return self._sold_quantity or 0
        return self.invoice_items.filter(invoice__status__in=_INVOICE_SALE_STATUSES).aggregate(total=Sum("quantity"))["total"] or 0

    def __str__(self):
        return self.name


class CartonPricing(models.Model):
    product = models.ForeignKey(Product, on_delete=models.PROTECT, related_name="carton_pricings", null=True, blank=True)
    name = models.CharField(max_length=200)
    units_per_carton = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    carton_price = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(Decimal("0"))])
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("name",)
        verbose_name = "Carton pricing"
        verbose_name_plural = "Carton pricings"
        constraints = [
            models.CheckConstraint(condition=Q(carton_price__gte=Decimal("0")), name="cartonpricing_carton_price_non_negative"),
            models.UniqueConstraint(fields=("product", "name"), name="cartonpricing_unique_product_name"),
        ]

    def __str__(self):
        return self.name
