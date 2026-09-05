from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [("products", "0006_product_category")]

    operations = [
        migrations.AddField(
            model_name="product",
            name="is_active",
            field=models.BooleanField(default=True, db_index=True),
        ),
        migrations.AddField(
            model_name="cartonpricing",
            name="product",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="carton_pricings",
                to="products.product",
            ),
        ),
        migrations.AddConstraint(
            model_name="cartonpricing",
            constraint=models.UniqueConstraint(
                fields=("product", "name"),
                name="cartonpricing_unique_product_name",
            ),
        ),
    ]
