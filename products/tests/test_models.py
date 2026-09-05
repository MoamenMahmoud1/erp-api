from decimal import Decimal

from django.test import TestCase

from products.models import CartonPricing, Product


class ProductModelTests(TestCase):
    def test_active_queryset(self):
        active = Product.objects.create(
            name="Active",
            purchase_price=Decimal("10"),
            selling_price=Decimal("20"),
        )
        inactive = Product.objects.create(
            name="Inactive",
            purchase_price=Decimal("10"),
            selling_price=Decimal("20"),
            is_active=False,
        )
        self.assertIn(active, Product.objects.active())
        self.assertNotIn(inactive, Product.objects.active())

    def test_carton_pricing_belongs_to_product(self):
        product = Product.objects.create(
            name="Product",
            purchase_price=Decimal("10"),
            selling_price=Decimal("20"),
        )
        carton = CartonPricing.objects.create(
            product=product,
            name="Case",
            units_per_carton=12,
            carton_price=Decimal("200"),
        )
        self.assertEqual(product.carton_pricings.get(), carton)
