from decimal import Decimal

from django.test import SimpleTestCase

from common.exceptions import InvalidMoney
from common.money import (
    from_minor_units,
    quantize_money,
    to_minor_units,
)


class MoneyContentionTests(SimpleTestCase):
    def test_quantize_money_rounds_half_up(self):
        # 1.005 rounds half-up to 1.01 (banker's/half-even would give 1.00).
        self.assertEqual(quantize_money(Decimal("1.005")), Decimal("1.01"))
        self.assertEqual(quantize_money(Decimal("1.004")), Decimal("1.00"))

    def test_quantize_money_rejects_float(self):
        with self.assertRaises(InvalidMoney):
            quantize_money(1.005)

    def test_minor_units_roundtrip(self):
        self.assertEqual(to_minor_units(Decimal("12.34")), 1234)
        self.assertEqual(from_minor_units(1234), Decimal("12.34"))

    def test_from_minor_units_quantizes(self):
        # Rounding to 2dp after scaling; 0.005 -> 0.01 half-up.
        self.assertEqual(from_minor_units(1), Decimal("0.01"))
        self.assertEqual(from_minor_units(1500), Decimal("15.00"))