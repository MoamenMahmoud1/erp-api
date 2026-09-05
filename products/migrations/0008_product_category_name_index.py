from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("products", "0007_product_is_active_cartonpricing_product_and_unique")]

    operations = [
        migrations.AddIndex(
            model_name="product",
            index=models.Index(
                fields=["category", "name"],
                name="products_product_cat_name_idx",
            ),
        ),
    ]
