from datetime import timedelta

from django.test import TestCase
from django.utils import timezone

from inventory.api.filters import StockMovementFilter
from inventory.models import StockMovement

from .helpers import InventoryTestMixin


class StockMovementFilterTests(InventoryTestMixin, TestCase):
    def test_filters_by_type_date_and_creator_name(self):
        movement = StockMovement.objects.create(
            movement_type=StockMovement.MovementType.TRANSFER,
            source_location=self.warehouse,
            destination_location=self.vehicle,
            created_by=self.user,
            reference="FILTER-REF",
        )
        StockMovement.objects.filter(pk=movement.pk).update(
            created_at=timezone.now() - timedelta(days=2)
        )
        filtered = StockMovementFilter(
            {
                "movement_type": "TRANSFER",
                "created_date_from": (timezone.localdate() - timedelta(days=3)).isoformat(),
                "created_date_to": (timezone.localdate() - timedelta(days=1)).isoformat(),
                "created_by_name": "stock-user",
            },
            queryset=StockMovement.objects.all(),
        ).qs
        self.assertEqual(list(filtered.values_list("pk", flat=True)), [movement.pk])
