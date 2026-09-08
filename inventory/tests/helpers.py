from decimal import Decimal

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission

from inventory.models import StockLocation
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
        self.product = Product.objects.create(
            name="Widget",
            purchase_price=Decimal("50.00"),
            selling_price=Decimal("100.00"),
        )
        self.warehouse = StockLocation.objects.create(
            name="Main Warehouse",
            location_type=StockLocation.LocationType.MAIN_WAREHOUSE,
        )
        self.vehicle = StockLocation.objects.create(
            name="Van 01",
            location_type=StockLocation.LocationType.SALES_VEHICLE,
            employee=self.user,
        )
