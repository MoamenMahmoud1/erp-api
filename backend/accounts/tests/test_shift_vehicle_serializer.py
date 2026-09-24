from django.test import SimpleTestCase

from accounts.api.serializers.shift import EmployeeShiftVehicleOptionSerializer


class EmployeeShiftVehicleOptionSerializerTests(SimpleTestCase):
    def test_serializer_exposes_only_vehicle_option_fields(self):
        serializer = EmployeeShiftVehicleOptionSerializer()
        self.assertEqual(tuple(serializer.fields), ("id", "name"))
        self.assertTrue(serializer.fields["id"].read_only)
        self.assertTrue(serializer.fields["name"].read_only)
