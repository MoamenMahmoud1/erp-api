from datetime import timedelta
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from accounting.models import Account, Expense
from accounting.services import ensure_default_accounts
from accounting.services.expenses import create_expense
from accounting.services.journal import create_journal_entry, post_journal_entry
from accounts.models import Employee
from customers.models import Customer
from coupons.models import Coupon
from inventory.models import StockLocation
from inventory.services.transfer_stock import transfer_stock
from invoices.models import Invoice, InvoiceItem
from invoices.services.lifecycle import confirm_invoice
from invoices.services.returns import create_sales_return
from organization.models import Company, Department, Site
from payments.services.collection import collect
from products.models import CartonPricing, Product
from purchases.models import Purchase, PurchaseItem
from purchases.services.confirm_purchase import ConfirmPurchaseService
from purchases.services.return_purchase import return_purchase
from purchases.services.supplier_payment import pay_supplier
from suppliers.models import Supplier
from django.contrib.auth import get_user_model


class Command(BaseCommand):
    help = "Create a realistic, interconnected demo dataset for the ERP."

    DEMO_ADMIN_USERNAME = "demo_admin"
    DEMO_ADMIN_EMAIL = "admin@niletradedemo.local"
    DEMO_PASSWORD = "DemoERP@2026!"

    def add_arguments(self, parser):
        parser.add_argument(
            "--force",
            action="store_true",
            help="Abort and recreate is not supported; this only allows reseeding when the demo sentinel exists.",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        User = get_user_model()

        if User.objects.filter(username=self.DEMO_ADMIN_USERNAME).exists():
            if not options["force"]:
                self.stdout.write(
                    self.style.WARNING(
                        "Demo data already exists. Use --force only after resetting the demo database."
                    )
                )
                return
            raise RuntimeError(
                "Refusing to duplicate demo business data. Reset the database or remove the demo sentinel first."
            )

        now = timezone.now()
        dates = [now - timedelta(days=offset) for offset in (6, 5, 4, 3, 2, 1, 0)]

        company = Company.objects.filter(singleton_marker=True).first()
        if company is None:
            company = Company.objects.create(
                name="Nile Trade Distribution",
                legal_name="Nile Trade Distribution LLC",
                registration_number="NTD-2026-004281",
                tax_number="EG-TR-583920174",
                email="hello@niletradedemo.local",
                phone="+20224581234",
                website="https://niletradedemo.local",
                singleton_marker=True,
            )
        else:
            company_updates = {
                "legal_name": company.legal_name or "Nile Trade Distribution LLC",
                "registration_number": company.registration_number or "NTD-2026-004281",
                "tax_number": company.tax_number or "EG-TR-583920174",
                "email": company.email or "hello@niletradedemo.local",
                "phone": company.phone or "+20224581234",
                "website": company.website or "https://niletradedemo.local",
            }
            for field, value in company_updates.items():
                setattr(company, field, value)
            company.save(update_fields=(*company_updates, "updated_at"))

        admin = User.objects.create_superuser(
            username=self.DEMO_ADMIN_USERNAME,
            email=self.DEMO_ADMIN_EMAIL,
            password=self.DEMO_PASSWORD,
            first_name="Omar",
            last_name="Hassan",
        )
        admin.is_verified = True
        admin.save(update_fields=("is_verified", "updated_at"))

        users = {
            "manager": self._create_user(User, "sara", "sara.elmasry@niletradedemo.local", "Sara", "Elmasry"),
            "sales_1": self._create_user(User, "ahmed", "ahmed.fathy@niletradedemo.local", "Ahmed", "Fathy"),
            "sales_2": self._create_user(User, "mariam", "mariam.adel@niletradedemo.local", "Mariam", "Adel"),
        }

        hq = Site.objects.create(
            company=company,
            code="HQ",
            name="Nile Trade Head Office",
            site_type=Site.Type.HEAD_OFFICE,
            address_line_1="14 Nile Corniche",
            city="Cairo",
            state_or_province="Cairo",
            postal_code="11511",
            country_code="EG",
            email="hq@niletradedemo.local",
            phone="+20224581234",
        )
        branch = Site.objects.create(
            company=company,
            code="BR01",
            name="Nasr City Distribution Branch",
            site_type=Site.Type.BRANCH,
            address_line_1="22 Abbas El Akkad St.",
            city="Cairo",
            state_or_province="Cairo",
            postal_code="11765",
            country_code="EG",
            email="branch@niletradedemo.local",
            phone="+20224191234",
        )
        Site.objects.create(
            company=company,
            parent=branch,
            code="ST01",
            name="Nasr City Retail Store",
            site_type=Site.Type.STORE,
            address_line_1="8 Makram Ebeid St.",
            city="Cairo",
            state_or_province="Cairo",
            postal_code="11765",
            country_code="EG",
            email="store@niletradedemo.local",
            phone="+20224031234",
        )

        sales_dept = Department.objects.create(
            company=company,
            site=branch,
            code="SALES",
            name="Sales",
            description="Field sales and customer accounts.",
        )
        finance_dept = Department.objects.create(
            company=company,
            site=hq,
            code="FIN",
            name="Finance",
            description="Accounting, collections, and treasury.",
        )
        warehouse_dept = Department.objects.create(
            company=company,
            site=branch,
            code="WH",
            name="Warehouse",
            description="Stock receiving and distribution.",
        )

        manager_employee = Employee.objects.create(
            user=users["manager"],
            work_site=branch,
            department=sales_dept,
        )
        sales_1_employee = Employee.objects.create(
            user=users["sales_1"],
            manager=manager_employee,
            work_site=branch,
            department=sales_dept,
        )
        sales_2_employee = Employee.objects.create(
            user=users["sales_2"],
            manager=manager_employee,
            work_site=branch,
            department=sales_dept,
        )
        Employee.objects.create(
            user=admin,
            work_site=hq,
            department=finance_dept,
        )
        manager_employee.save()
        sales_1_employee.save()
        sales_2_employee.save()

        customers = {
            "cairo_retail": Customer.objects.create(
                name="Cairo Retail Hub",
                phone="+201022345678",
                address="Heliopolis, Cairo",
            ),
            "delta_market": Customer.objects.create(
                name="Delta Market Chain",
                phone="+201011223344",
                address="Mansoura, Dakahlia",
            ),
            "nile_mini": Customer.objects.create(
                name="Nile Mini Markets",
                phone="+201099887766",
                address="Nasr City, Cairo",
            ),
            "almanara": Customer.objects.create(
                name="Al-Manara Hospitality",
                phone="+201015551234",
                address="New Cairo, Cairo",
            ),
            "fresh_corner": Customer.objects.create(
                name="Fresh Corner Grocers",
                phone="+201012009988",
                address="Giza, Giza",
            ),
            "walk_in": Customer.objects.create(
                name="Walk-in Retail Customer",
                phone="+201000000111",
                address="Cairo",
            ),
        }

        suppliers = {
            "delta_foods": Supplier.objects.create(
                name="Delta Foods Wholesale",
                phone="+20225184567",
                email="orders@deltafoods.local",
                address="10 El Gomhoria St., Mansoura",
            ),
            "nile_fmcg": Supplier.objects.create(
                name="Nile FMCG Supply",
                phone="+20233457891",
                email="sales@nilefmcg.local",
                address="45 Industrial Zone, Obour",
            ),
            "cairo_home": Supplier.objects.create(
                name="Cairo Home & Hygiene",
                phone="+20222673456",
                email="accounts@cairohome.local",
                address="18 El Salam City, Cairo",
            ),
            "inactive_supplier": Supplier.objects.create(
                name="Old Alexandria Supplies",
                phone="+2034872211",
                email="legacy@alexsupplies.local",
                address="Alexandria",
                is_active=False,
            ),
        }

        products = {}
        product_specs = [
            ("basmati_rice", "Premium Basmati Rice 5kg", "Grocery", "70.00", "95.00"),
            ("sunflower_oil", "Pure Sunflower Oil 1L", "Grocery", "60.00", "78.00"),
            ("detergent", "UltraClean Laundry Detergent 2.5kg", "Household", "100.00", "140.00"),
            ("tissues", "SoftCare Facial Tissues 200 Sheets", "Household", "45.00", "65.00"),
            ("water", "NileSpring Mineral Water 1.5L (6 Pack)", "Beverages", "55.00", "90.00"),
            ("coffee", "Arabica Coffee 500g", "Beverages", "120.00", "180.00"),
            ("tomato", "Classic Tomato Paste 400g", "Grocery", "35.00", "55.00"),
            ("dishwash", "BrightDrop Dishwashing Liquid 750ml", "Household", "50.00", "75.00"),
            ("archived", "Legacy Barcode Scanner Cable", "Equipment", "90.00", "120.00"),
        ]
        for key, name, category, purchase_price, selling_price in product_specs:
            products[key] = Product.objects.create(
                name=name,
                category=category,
                purchase_price=Decimal(purchase_price),
                selling_price=Decimal(selling_price),
                is_active=key != "archived",
            )

        for product_key, name, units_per_carton, carton_price in (
            ("basmati_rice", "Rice Carton", 5, "450.00"),
            ("sunflower_oil", "Oil Carton", 12, "840.00"),
            ("water", "Water Case", 6, "510.00"),
            ("tissues", "Tissues Carton", 24, "1380.00"),
        ):
            CartonPricing.objects.create(
                product=products[product_key],
                name=name,
                units_per_carton=units_per_carton,
                carton_price=Decimal(carton_price),
            )

        coupon = Coupon.objects.create(
            code="WELCOME10",
            discount_type=Coupon.DiscountType.PERCENTAGE,
            discount_value=Decimal("10"),
            minimum_invoice_amount=Decimal("1000"),
            is_active=True,
            valid_from=now - timedelta(days=30),
            valid_until=now + timedelta(days=30),
        )

        warehouse = StockLocation.objects.create(
            name="Main Warehouse - Nasr City",
            location_type=StockLocation.LocationType.MAIN_WAREHOUSE,
            is_active=True,
        )
        sales_locations = {
            "sales_1": StockLocation.objects.create(
                name="Van 01 - Ahmed Fathy",
                location_type=StockLocation.LocationType.SALES_VEHICLE,
                employee=users["sales_1"],
                is_active=True,
            ),
            "sales_2": StockLocation.objects.create(
                name="Van 02 - Mariam Adel",
                location_type=StockLocation.LocationType.SALES_VEHICLE,
                employee=users["sales_2"],
                is_active=True,
            ),
            "manager": StockLocation.objects.create(
                name="Van 03 - Sara Elmasry",
                location_type=StockLocation.LocationType.SALES_VEHICLE,
                employee=users["manager"],
                is_active=True,
            ),
        }

        accounts = ensure_default_accounts(company)
        equity_account, _ = Account.objects.get_or_create(
            company=company,
            code="3000",
            defaults={"name": "Owner Equity", "account_type": Account.AccountType.EQUITY},
        )
        operating_expense, _ = Account.objects.get_or_create(
            company=company,
            code="5200",
            defaults={"name": "Operating Expenses", "account_type": Account.AccountType.EXPENSE},
        )

        self._post_opening_balance(
            company=company,
            actor_id=admin.pk,
            cash_account=accounts["cash"],
            bank_account=accounts["bank"],
            equity_account=equity_account,
            entry_date=timezone.localdate(dates[0]),
        )

        purchases = []
        purchases.append(
            self._create_purchase(
                supplier=suppliers["delta_foods"],
                actor=admin,
                when=dates[0],
                reference="PO-2026-0901",
                items=[
                    (products["basmati_rice"], 100, "70.00"),
                    (products["sunflower_oil"], 80, "60.00"),
                    (products["detergent"], 50, "100.00"),
                ],
            )
        )
        purchases.append(
            self._create_purchase(
                supplier=suppliers["nile_fmcg"],
                actor=admin,
                when=dates[1],
                reference="PO-2026-0902",
                items=[
                    (products["tissues"], 100, "45.00"),
                    (products["water"], 150, "55.00"),
                    (products["coffee"], 60, "120.00"),
                ],
            )
        )
        purchases.append(
            self._create_purchase(
                supplier=suppliers["cairo_home"],
                actor=admin,
                when=dates[2],
                reference="PO-2026-0903",
                items=[
                    (products["tomato"], 100, "35.00"),
                    (products["dishwash"], 80, "50.00"),
                    (products["basmati_rice"], 50, "72.00"),
                    (products["sunflower_oil"], 40, "62.00"),
                ],
            )
        )

        return_purchase(
            purchase_id=purchases[0].pk,
            created_by_id=admin.pk,
            actor=admin,
            reason="Packaging damage identified during receiving inspection",
            items=[
                {"purchase_item": purchases[0].items.get(product=products["basmati_rice"]), "quantity": 5}
            ],
        )

        pay_supplier(
            supplier=suppliers["delta_foods"],
            cash_amount=Decimal("3000.00"),
            transfer_amount=Decimal("0.00"),
            paid_by_id=admin.pk,
            actor=admin,
            reference="SUP-PAY-0903",
        )
        pay_supplier(
            supplier=suppliers["nile_fmcg"],
            cash_amount=Decimal("0.00"),
            transfer_amount=Decimal("6000.00"),
            paid_by_id=admin.pk,
            actor=admin,
            reference="SUP-PAY-0906",
        )

        transfer_stock(
            source_id=warehouse.pk,
            destination_id=sales_locations["sales_1"].pk,
            created_by=admin,
            reference="LOAD-0904-AHMED",
            items=[
                {"product": products["basmati_rice"], "quantity": 30},
                {"product": products["sunflower_oil"], "quantity": 25},
                {"product": products["detergent"], "quantity": 20},
                {"product": products["dishwash"], "quantity": 15},
            ],
        )
        transfer_stock(
            source_id=warehouse.pk,
            destination_id=sales_locations["sales_2"].pk,
            created_by=admin,
            reference="LOAD-0904-MARIAM",
            items=[
                {"product": products["water"], "quantity": 60},
                {"product": products["coffee"], "quantity": 25},
                {"product": products["detergent"], "quantity": 20},
                {"product": products["tissues"], "quantity": 20},
            ],
        )
        transfer_stock(
            source_id=warehouse.pk,
            destination_id=sales_locations["manager"].pk,
            created_by=admin,
            reference="LOAD-0904-SARA",
            items=[
                {"product": products["basmati_rice"], "quantity": 25},
                {"product": products["water"], "quantity": 60},
                {"product": products["tomato"], "quantity": 25},
                {"product": products["dishwash"], "quantity": 20},
                {"product": products["coffee"], "quantity": 20},
            ],
        )

        invoices = []
        invoices.append(
            self._create_invoice(
                customer=customers["cairo_retail"],
                actor=admin,
                created_by=users["sales_1"],
                when=dates[2],
                items=[
                    (products["basmati_rice"], 12),
                    (products["sunflower_oil"], 8),
                    (products["detergent"], 3),
                ],
                coupon=coupon,
                discount=Decimal("218.40"),
            )
        )
        invoices.append(
            self._create_invoice(
                customer=customers["delta_market"],
                actor=admin,
                created_by=users["sales_2"],
                when=dates[2],
                items=[
                    (products["coffee"], 6),
                    (products["tissues"], 10),
                ],
            )
        )
        invoices.append(
            self._create_invoice(
                customer=customers["nile_mini"],
                actor=admin,
                created_by=users["manager"],
                when=dates[1],
                items=[
                    (products["water"], 20),
                    (products["tomato"], 12),
                ],
            )
        )
        invoices.append(
            self._create_invoice(
                customer=customers["almanara"],
                actor=admin,
                created_by=users["sales_1"],
                when=dates[1],
                items=[
                    (products["detergent"], 8),
                    (products["dishwash"], 10),
                    (products["basmati_rice"], 5),
                ],
            )
        )
        invoices.append(
            self._create_invoice(
                customer=customers["fresh_corner"],
                actor=admin,
                created_by=users["sales_2"],
                when=dates[0],
                items=[
                    (products["coffee"], 4),
                    (products["water"], 12),
                ],
            )
        )
        invoices.append(
            self._create_invoice(
                customer=customers["walk_in"],
                actor=admin,
                created_by=users["manager"],
                when=dates[0],
                items=[
                    (products["basmati_rice"], 15),
                    (products["water"], 10),
                ],
            )
        )

        collect(
            customer=customers["cairo_retail"],
            cash_amount=invoices[0].total,
            transfer_amount=Decimal("0.00"),
            collected_by_id=admin.pk,
            actor=admin,
        )
        collect(
            customer=customers["delta_market"],
            cash_amount=Decimal("0.00"),
            transfer_amount=Decimal("800.00"),
            collected_by_id=admin.pk,
            actor=admin,
        )
        collect(
            customer=customers["almanara"],
            cash_amount=Decimal("0.00"),
            transfer_amount=invoices[3].total,
            collected_by_id=admin.pk,
            actor=admin,
        )

        create_sales_return(
            invoice_id=invoices[3].pk,
            created_by_id=admin.pk,
            actor=admin,
            reason="Customer returned two unopened rice units",
            items=[
                {"invoice_item": invoices[3].items.get(product=products["basmati_rice"]), "quantity": 2}
            ],
        )

        create_expense(
            amount=Decimal("2500.00"),
            expense_account=operating_expense.pk,
            payment_account=accounts["cash"].pk,
            expense_date=timezone.localdate(dates[0]),
            description="Warehouse utilities and local delivery fuel",
            reference="EXP-2026-0907",
            created_by_id=admin.pk,
            company=company,
        )

        draft_purchase = Purchase.objects.create(
            supplier=suppliers["delta_foods"],
            created_by=admin,
            reference="PO-DRAFT-2026-0910",
        )
        PurchaseItem.objects.create(
            purchase=draft_purchase,
            product=products["coffee"],
            quantity=20,
            unit_purchase_price=Decimal("122.00"),
        )

        draft_invoice = Invoice.objects.create(
            customer=customers["walk_in"],
            created_by=users["sales_2"],
            status=Invoice.Status.DRAFT,
        )
        InvoiceItem.objects.create(
            invoice=draft_invoice,
            product=products["dishwash"],
            quantity=4,
            unit_price=products["dishwash"].selling_price,
            cost_price=products["dishwash"].purchase_price,
        )

        self.stdout.write(self.style.SUCCESS("Realistic ERP demo data created successfully."))
        self.stdout.write("")
        self.stdout.write("Demo login:")
        self.stdout.write(f"  username: {self.DEMO_ADMIN_USERNAME}")
        self.stdout.write(f"  password: {self.DEMO_PASSWORD}")
        self.stdout.write("")
        self.stdout.write("Data includes:")
        self.stdout.write("  - Company, sites, departments, employees and sales vehicles")
        self.stdout.write("  - 6 customers and 4 suppliers (including one inactive supplier)")
        self.stdout.write("  - 9 products, carton pricing, coupon and archived product")
        self.stdout.write("  - Purchases, purchase return, supplier payments")
        self.stdout.write("  - Sales across 3 employees, full + partial collections")
        self.stdout.write("  - Sales return + refund, operating expense, opening balance")
        self.stdout.write("  - Draft purchase and draft invoice for lifecycle screens")
        self.stdout.write("  - Posted accounting entries feeding P&L / BS / CF / AR / AP / analytics")

    @staticmethod
    def _create_user(User, username, email, first_name, last_name):
        return User.objects.create_user(
            username=username,
            email=email,
            password="DemoERP@2026!",
            first_name=first_name,
            last_name=last_name,
            is_active=True,
            is_verified=True,
        )

    @staticmethod
    def _create_purchase(*, supplier, actor, when, reference, items):
        purchase = Purchase.objects.create(
            supplier=supplier,
            created_by=actor,
            reference=reference,
        )
        for product, quantity, unit_price in items:
            PurchaseItem.objects.create(
                purchase=purchase,
                product=product,
                quantity=quantity,
                unit_purchase_price=Decimal(unit_price),
            )
        Purchase.objects.filter(pk=purchase.pk).update(created_at=when)
        purchase.refresh_from_db()
        ConfirmPurchaseService.execute(purchase_id=purchase.pk, actor=actor)
        return purchase

    @staticmethod
    def _create_invoice(*, customer, actor, created_by, when, items, coupon=None, discount=Decimal("0")):
        invoice = Invoice.objects.create(
            customer=customer,
            created_by=created_by,
            coupon=coupon,
            coupon_discount=discount,
        )
        for product, quantity in items:
            InvoiceItem.objects.create(
                invoice=invoice,
                product=product,
                quantity=quantity,
                unit_price=product.selling_price,
                cost_price=product.purchase_price,
            )
        Invoice.objects.filter(pk=invoice.pk).update(created_at=when)
        invoice.refresh_from_db()
        confirm_invoice(invoice.pk, actor=actor)
        return invoice

    @staticmethod
    def _post_opening_balance(*, company, actor_id, cash_account, bank_account, equity_account, entry_date):
        entry = create_journal_entry(
            company=company,
            created_by_id=actor_id,
            entry_date=entry_date,
            description="Demo opening balance",
            reference="OPENING-DEMO-2026",
            source_type="demo.opening_balance",
            source_id=1,
            lines=[
                {"account_id": cash_account.pk, "debit": Decimal("150000.00"), "credit": 0},
                {"account_id": bank_account.pk, "debit": Decimal("100000.00"), "credit": 0},
                {"account_id": equity_account.pk, "debit": 0, "credit": Decimal("250000.00")},
            ],
        )
        post_journal_entry(entry_id=entry.pk, actor_id=actor_id, company=company)
