"""Canonical source references for stock movements."""

from inventory.models import StockMovement


def build_source_reference(*, source_type, source_id, label=""):
    """Build a stable machine-readable prefix with an optional human label."""
    prefix = f"source:{source_type}:{source_id}"
    return f"{prefix} | {label}" if label else prefix


def find_source_movement(*, source_type, source_id, movement_type=None, legacy_reference=None):
    """Find a movement by canonical source identity, with one legacy fallback."""
    queryset = StockMovement.objects.filter(
        reference__startswith=f"source:{source_type}:{source_id}",
    )
    if movement_type is not None:
        queryset = queryset.filter(movement_type=movement_type)
    movement = queryset.order_by("-id").first()
    if movement is not None or not legacy_reference:
        return movement

    queryset = StockMovement.objects.filter(reference=legacy_reference)
    if movement_type is not None:
        queryset = queryset.filter(movement_type=movement_type)
    return queryset.order_by("-id").first()
