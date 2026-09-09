from rest_framework import serializers

from accounts.models import EmployeeShift
from inventory.models import StockLocation


class EmployeeShiftSerializer(serializers.ModelSerializer):
    employee_name = serializers.SerializerMethodField()
    site_name = serializers.CharField(source="site.name", read_only=True)
    vehicle_name = serializers.CharField(source="vehicle.name", read_only=True, allow_null=True)

    class Meta:
        model = EmployeeShift
        fields = (
            "id", "employee", "employee_name", "site", "site_name", "vehicle", "vehicle_name",
            "business_date", "status", "opened_at", "closed_at", "opening_cash", "closing_cash",
            "closing_transfer", "closing_notes",
        )
        read_only_fields = fields

    def get_employee_name(self, obj):
        return str(obj.employee)


class StartEmployeeShiftSerializer(serializers.Serializer):
    opening_cash = serializers.DecimalField(max_digits=14, decimal_places=2, min_value=0, required=False, default="0.00")
    vehicle = serializers.PrimaryKeyRelatedField(
        queryset=StockLocation.objects.filter(location_type="SALES_VEHICLE", is_active=True),
        required=False,
        allow_null=True,
    )


class CloseEmployeeShiftSerializer(serializers.Serializer):
    closing_cash = serializers.DecimalField(max_digits=14, decimal_places=2, min_value=0)
    closing_transfer = serializers.DecimalField(max_digits=14, decimal_places=2, min_value=0)
    closing_notes = serializers.CharField(required=False, allow_blank=True, max_length=500)
