from decimal import Decimal

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission

from accounts.models import Employee
from inventory.models import StockLocation
from organization.models import Company, Site
from products.models import Product


class InventoryTestMixin:
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(
            username="stock-user",
            email="stock@example.com",
            password="StrongPass123!",
            is_staff=True,
        )
        permissions = Permission.objects.filter(
            content_type__app_label="inventory",
            codename__in=(
                "view_stocklocation",
                "view_stockbalance",
                "view_stockmovement",
                "transfer_stock",
            ),
        )
        self.user.user_permissions.set(permissions)
        self.company = Company.objects.create(name="Inventory Test Company")
        self.site = Site.objects.create(
            company=self.company,
            code="INV-ST",
            name="Inventory Test Branch",
            site_type=Site.Type.BRANCH,
            address_line_1="Test address",
            city="Cairo",
            country_code="EG",
        )
        Employee.objects.create(user=self.user, work_site=self.site)
        self.product = Product.objects.create(
            name="Widget",
            purchase_price=Decimal("50.00"),
            selling_price=Decimal("100.00"),
        )
        self.warehouse = StockLocation.objects.create(
            name="Main Warehouse",
            location_type=StockLocation.LocationType.MAIN_WAREHOUSE,
            site=self.site,
        )
        self.vehicle = StockLocation.objects.create(
            name="Van 01",
            location_type=StockLocation.LocationType.SALES_VEHICLE,
            employee=self.user,
            site=self.site,
        )
