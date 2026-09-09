from django.db import migrations, models


def initialize_counters(apps, schema_editor):
    Company = apps.get_model("organization", "Company")
    Product = apps.get_model("products", "Product")
    Invoice = apps.get_model("invoices", "Invoice")
    Customer = apps.get_model("customers", "Customer")
    Supplier = apps.get_model("suppliers", "Supplier")

    company = Company.objects.filter(singleton_marker=True).first()
    if company is None:
        return

    company.product_count = Product.objects.count()
    company.invoice_count = Invoice.objects.count()
    company.customer_count = Customer.objects.count()
    company.supplier_count = Supplier.objects.count()
    company.save(
        update_fields=(
            "product_count",
            "invoice_count",
            "customer_count",
            "supplier_count",
            "updated_at",
        )
    )


class Migration(migrations.Migration):
    dependencies = [
        ("organization", "0004_department"),
        ("products", "0008_rename_products_product_category_name_idx_products_product_cat_name_idx"),
        ("invoices", "0009_invoiceitem_cost_price"),
        ("customers", "0001_initial"),
        ("suppliers", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="company",
            name="counters_reconciled_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="company",
            name="customer_count",
            field=models.PositiveBigIntegerField(default=0),
        ),
        migrations.AddField(
            model_name="company",
            name="invoice_count",
            field=models.PositiveBigIntegerField(default=0),
        ),
        migrations.AddField(
            model_name="company",
            name="product_count",
            field=models.PositiveBigIntegerField(default=0),
        ),
        migrations.AddField(
            model_name="company",
            name="supplier_count",
            field=models.PositiveBigIntegerField(default=0),
        ),
        migrations.RunPython(initialize_counters, migrations.RunPython.noop),
    ]
