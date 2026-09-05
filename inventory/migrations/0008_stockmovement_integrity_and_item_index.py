from django.db import migrations, models
from django.db.models import F, Q


class Migration(migrations.Migration):
    dependencies = [
        ("inventory", "0007_stockmovement_permissions"),
    ]

    operations = [
        migrations.AddConstraint(
            model_name="stockmovement",
            constraint=models.CheckConstraint(
                condition=(
                    Q(
                        movement_type="TRANSFER",
                        source_location__isnull=False,
                        destination_location__isnull=False,
                    )
                    | Q(
                        movement_type__in=("PURCHASE_RETURN", "SALE"),
                        source_location__isnull=False,
                        destination_location__isnull=True,
                    )
                    | Q(
                        movement_type__in=("PURCHASE", "SALEABLE_RETURN", "DAMAGED_RETURN"),
                        source_location__isnull=True,
                        destination_location__isnull=False,
                    )
                ),
                name="stock_movement_direction_matches_type",
            ),
        ),
        migrations.AddConstraint(
            model_name="stockmovement",
            constraint=models.CheckConstraint(
                condition=(
                    Q(movement_type__in=("TRANSFER",), source_location__isnull=True)
                    | ~Q(source_location=F("destination_location"))
                ),
                name="stock_transfer_locations_differ",
            ),
        ),
        migrations.AddIndex(
            model_name="stockmovementitem",
            index=models.Index(
                fields=("product", "movement"),
                name="stock_move_item_product_idx",
            ),
        ),
    ]
