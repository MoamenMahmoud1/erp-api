from django.test import TestCase
from django.utils import timezone

from accounts.models import CustomUserModel
from customers.models import Customer
from invoices.models import Invoice
from organization.models import Company
from organization.services.metrics import reconcile_company_counters
from organization.tasks import reconcile_company_counters_task
from products.models import Product
from suppliers.models import Supplier


class CompanyCounterTests(TestCase):
    def setUp(self):
        self.company = Company.objects.create(name="Counter Test Company")

    def test_master_data_counters_update_on_create_and_delete(self):
        customer = Customer.objects.create(name="Customer")
        supplier = Supplier.objects.create(name="Supplier")
        product = Product.objects.create(
            name="Product",
            purchase_price="10.00",
            selling_price="15.00",
        )
        user = CustomUserModel.objects.create_user(
            username="counter-user",
            email="counter@example.com",
            password="strong-password-123",
        )
        invoice = Invoice.objects.create(customer=customer, created_by=user)

        self.company.refresh_from_db()
        self.assertEqual(self.company.customer_count, 1)
        self.assertEqual(self.company.supplier_count, 1)
        self.assertEqual(self.company.product_count, 1)
        self.assertEqual(self.company.invoice_count, 1)

        invoice.delete()
        product.delete()
        supplier.delete()
        customer.delete()

        self.company.refresh_from_db()
        self.assertEqual(self.company.customer_count, 0)
        self.assertEqual(self.company.supplier_count, 0)
        self.assertEqual(self.company.product_count, 0)
        self.assertEqual(self.company.invoice_count, 0)

    def test_reconciliation_repairs_counter_drift(self):
        Customer.objects.create(name="Customer")
        Product.objects.create(
            name="Product",
            purchase_price="10.00",
            selling_price="15.00",
        )
        Supplier.objects.create(name="Supplier")

        Company.objects.filter(pk=self.company.pk).update(
            customer_count=99,
            product_count=99,
            supplier_count=99,
            invoice_count=99,
            counters_reconciled_at=None,
        )

        counts = reconcile_company_counters()

        self.company.refresh_from_db()
        self.assertEqual(counts, {
            "product_count": 1,
            "invoice_count": 0,
            "customer_count": 1,
            "supplier_count": 1,
        })
        self.assertEqual(self.company.product_count, 1)
        self.assertEqual(self.company.customer_count, 1)
        self.assertEqual(self.company.supplier_count, 1)
        self.assertEqual(self.company.invoice_count, 0)
        self.assertIsNotNone(self.company.counters_reconciled_at)

    def test_celery_reconciliation_task_runs_the_same_service(self):
        result = reconcile_company_counters_task.run()
        self.assertEqual(result["product_count"], 0)
        self.assertIsNotNone(
            Company.objects.get(pk=self.company.pk).counters_reconciled_at
        )

    def test_reconciliation_time_is_timezone_aware(self):
        reconcile_company_counters()
        timestamp = Company.objects.get(pk=self.company.pk).counters_reconciled_at
        self.assertIsNotNone(timestamp)
        self.assertTrue(timezone.is_aware(timestamp))
