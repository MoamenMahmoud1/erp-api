"""
Backend money convention (see docs/MONEY_CONVENTION.md).

The backend stores monetary values as ``Decimal`` (never ``float``) and
performs all money arithmetic with 2-decimal precision and ``ROUND_HALF_UP``.

This module is deliberately small and function-based. It exists to:

- centralize currency precision / rounding
- validate that money is never negative where the business rule forbids it
- quantify money to the canonical 2-decimal representation
- optionally convert to/from integer minor units (useful when coordinating
  with the Flutter ``Money`` type that works in minor units)

It is NOT a Money framework: no classes, no operator overloading, no currency
registry. Use it where explicit validation or quantization is needed.
"""

from decimal import ROUND_HALF_UP, Decimal

from common.exceptions import InvalidMoney

# Canonical money precision for persisted values.
CURRENCY_PLACES = 2
# Smallest representable money unit (one cent / 0.01 of the currency).
CURRENCY_UNIT = Decimal("0.01")
# Deterministic rounding for all currency arithmetic.
ROUNDING = ROUND_HALF_UP
# Per-unit multiplier to convert a Decimal amount into integer minor units
# (the convention used by the Flutter client's Money type).
MINOR_UNIT_SCALE = 100


def money_decimal(value) -> Decimal:
    """Coerce ``value`` to :class:`Decimal`, rejecting float.

    Using raw floats for money is prohibited because binary floats cannot
    represent many decimal values exactly, which breaks determinism.
    """
    if isinstance(value, float):
        raise InvalidMoney("Float values are not allowed for money.")
    return Decimal(value)


def quantize_money(value) -> Decimal:
    """Return ``value`` rounded to currency precision with ROUND_HALF_UP."""
    return money_decimal(value).quantize(CURRENCY_UNIT, rounding=ROUNDING)


def to_minor_units(value) -> int:
    """Return the integer minor-unit representation of a Decimal amount."""
    return int(quantize_money(value) * MINOR_UNIT_SCALE)


def from_minor_units(value: int) -> Decimal:
    """Build a Decimal amount from integer minor units."""
    return quantize_money(Decimal(int(value)) / MINOR_UNIT_SCALE)


def ensure_non_negative(value) -> Decimal:
    """Quantize a monetary value and reject negatives unless policy allows."""
    amount = quantize_money(value)
    if amount < 0:
        raise InvalidMoney("Monetary value must not be negative.")
    return amount