from django.db import IntegrityError, transaction
from django.test import TestCase

from inventory.models import StockLocation
from organization.models import Company, Site


class BranchStockLocationTests(TestCase):
    def setUp(self):
        self.company = Company.objects.create(name="Test Company")
        self.branch_a = Site.objects.create(
            company=self.company,
            code="BR-A",
            name="Branch A",
            site_type=Site.Type.BRANCH,
            address_line_1="A",
            city="Cairo",
            country_code="EG",
        )
        self.branch_b = Site.objects.create(
            company=self.company,
            code="BR-B",
            name="Branch B",
            site_type=Site.Type.BRANCH,
            address_line_1="B",
            city="Cairo",
            country_code="EG",
        )

    def make_warehouse(self, site, name):
        return StockLocation.objects.create(
            site=site,
            name=name,
            location_type=StockLocation.LocationType.MAIN_WAREHOUSE,
        )

    def test_each_branch_can_have_its_own_main_warehouse(self):
        first = self.make_warehouse(self.branch_a, "A Warehouse")
        second = self.make_warehouse(self.branch_b, "B Warehouse")
        self.assertNotEqual(first.pk, second.pk)

    def test_branch_cannot_have_two_active_main_warehouses(self):
        self.make_warehouse(self.branch_a, "A Warehouse")
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                self.make_warehouse(self.branch_a, "A Warehouse 2")
