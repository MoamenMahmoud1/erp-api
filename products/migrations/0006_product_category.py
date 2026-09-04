from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("products", "0005_remove_product_stock_quantity"),
    ]

    operations = [
        migrations.AddField(
            model_name="product",
            name="category",
            field=models.CharField(db_index=True, default="General", max_length=100),
        ),
        migrations.AlterModelOptions(
            name="product",
            options={"ordering": ("category", "name")},
        ),
        migrations.AddIndex(
            model_name="product",
            index=models.Index(
                fields=["category", "name"],
                name="products_product_category_name_idx",
            ),
        ),
    ]
