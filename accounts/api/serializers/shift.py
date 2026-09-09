from rest_framework import serializers

from accounts.models import EmployeeShift


class EmployeeShiftSerializer(serializers.ModelSerializer):
    employee_name = serializers.CharField(source="employee.__str__", read_only=True)
    site_name = serializers.CharField(source="site.name", read_only=True)
    vehicle_name = serializers.CharField(source="vehicle.name", read_only=True, allow_null=True)

    class Meta:
        model = EmployeeShift
        fields = (
            "id",
            "employee",
            "employee_name",
            "site",
            "site_name",
            "vehicle",
            "vehicle_name",
            "business_date",
            "status",
            "opened_at",
            "closed_at",
            "opening_cash",
            "closing_cash",
            "closing_transfer",
            "closing_notes",
        )
        read_only_fields = fields


class StartEmployeeShiftSerializer(serializers.Serializer):
    opening_cash = serializers.DecimalField(max_digits=14, decimal_places=2, min_value=0, required=False, default="0.00")
    vehicle = serializers.PrimaryKeyRelatedField(required=False, allow_null=True, queryset=EmployeeShift._meta.get_field("vehicle").remote_field.model.objects.filter(location_type="SALES_VEHICLE", is_active=True))


class CloseEmployeeShiftSerializer(serializers.Serializer):
    closing_cash = serializers.DecimalField(max_digits=14, decimal_places=2, min_value=0)
    closing_transfer = serializers.DecimalField(max_digits=14, decimal_places=2, min_value=0)
    closing_notes = serializers.CharField(required=False, allow_blank=True, max_length=500)
