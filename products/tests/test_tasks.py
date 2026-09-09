from datetime import date
from unittest.mock import patch

from django.test import SimpleTestCase

from products.tasks import refresh_product_intelligence


class ProductIntelligenceTaskTests(SimpleTestCase):
    @patch("products.tasks.product_intelligence")
    def test_refresh_product_intelligence_passes_as_of(self, product_service):
        refresh_product_intelligence.run(as_of=date(2026, 9, 8))
        product_service.assert_called_once_with(as_of=date(2026, 9, 8))
