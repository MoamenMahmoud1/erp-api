from django.db import IntegrityError

from rest_framework import generics, status
from rest_framework.response import Response

from accounts.api.serializers.shift import (
    CloseEmployeeShiftSerializer,
    EmployeeShiftSerializer,
    EmployeeShiftVehicleOptionSerializer,
    StartEmployeeShiftSerializer,
)
from accounts.models import EmployeeShift, Role
from accounts.permissions.shift import EmployeeShiftPermission
from accounts.services.employee_shift import (
    ShiftError,
    close_shift,
    current_shift_for_user,
    employee_for_user,
    start_shift,
)
from inventory.models import StockLocation
from services.organization_scope import visible_site_ids


class CurrentEmployeeShiftView(generics.GenericAPIView):
    permission_classes = (EmployeeShiftPermission,)

    def get(self, request, *args, **kwargs):
        shift = current_shift_for_user(request.user)
        if shift is None:
            return Response(None)
        return Response(EmployeeShiftSerializer(shift).data)


class EmployeeShiftVehicleOptionsView(generics.ListAPIView):
    permission_classes = (EmployeeShiftPermission,)
    permission_codename = "accounts.start_employee_shift"
    serializer_class = EmployeeShiftVehicleOptionSerializer

    def get_queryset(self):
        employee = employee_for_user(self.request.user, required=False)
        if employee is None or employee.work_site_id is None:
            return StockLocation.objects.none()
        return StockLocation.objects.filter(
            site_id=employee.work_site_id,
            employee_id=employee.user_id,
            location_type=StockLocation.LocationType.SALES_VEHICLE,
            is_active=True,
        ).order_by("name", "id")


class StartEmployeeShiftView(generics.GenericAPIView):
    permission_classes = (EmployeeShiftPermission,)
    serializer_class = StartEmployeeShiftSerializer
    permission_codename = "accounts.start_employee_shift"

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            vehicle = serializer.validated_data.get("vehicle")
            shift = start_shift(
                user=request.user,
                opening_cash=serializer.validated_data.get("opening_cash", "0.00"),
                vehicle_id=vehicle.pk if vehicle else None,
            )
        except (ShiftError, IntegrityError) as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_409_CONFLICT)
        return Response(EmployeeShiftSerializer(shift).data, status=status.HTTP_201_CREATED)


class CloseEmployeeShiftView(generics.GenericAPIView):
    permission_classes = (EmployeeShiftPermission,)
    serializer_class = CloseEmployeeShiftSerializer
    permission_codename = "accounts.close_employee_shift"

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            shift, totals = close_shift(
                user=request.user,
                closing_cash=serializer.validated_data["closing_cash"],
                closing_transfer=serializer.validated_data["closing_transfer"],
                notes=serializer.validated_data.get("closing_notes", ""),
            )
        except ShiftError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_409_CONFLICT)

        data = EmployeeShiftSerializer(shift).data
        data.update(
            {
                "expected_cash": str(totals["expected_cash"]),
                "cash_difference": str(shift.closing_cash - totals["expected_cash"]),
                "expected_transfer": str(totals["expected_transfer"]),
                "transfer_difference": str(shift.closing_transfer - totals["expected_transfer"]),
            }
        )
        return Response(data)


class EmployeeShiftListView(generics.ListAPIView):
    permission_classes = (EmployeeShiftPermission,)
    permission_codename = "accounts.view_all_employee_shifts"
    serializer_class = EmployeeShiftSerializer

    def get_queryset(self):
        queryset = EmployeeShift.objects.select_related("employee__user", "site", "vehicle").order_by("-business_date", "-opened_at")
        if Role.scope_for_user(self.request.user) == Role.Scope.COMPANY:
            return queryset
        sites = visible_site_ids(self.request.user)
        if sites is None:
            return queryset
        return queryset.filter(site_id__in=sites)
