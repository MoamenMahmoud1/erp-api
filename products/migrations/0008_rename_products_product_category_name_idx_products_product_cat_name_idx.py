from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("products", "0007_product_is_active_cartonpricing_product_and_unique"),
    ]

    operations = [
        migrations.RenameIndex(
            model_name="product",
            old_name="products_product_category_name_idx",
            new_name="products_product_cat_name_idx",
        ),
    ]
