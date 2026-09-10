from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import Employee, EmployeeShift, RoleProfile


class CurrentUserView(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        user = request.user
        employee = (
            Employee.objects.select_related("work_site", "department")
            .filter(user_id=user.pk)
            .first()
        )
        role = RoleProfile.summary_for_user(user)
        current_shift = None
        if employee:
            current_shift = (
                EmployeeShift.objects.select_related("site", "vehicle")
                .filter(employee=employee, status=EmployeeShift.Status.OPEN)
                .first()
            )

        return Response(
            {
                "id": user.pk,
                "username": user.username,
                "email": user.email,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "is_staff": user.is_staff,
                "is_superuser": user.is_superuser,
                "role_level": RoleProfile.level_for_user(user),
                "permissions": sorted(user.get_all_permissions()),
                "role": role,
                "employee": (
                    {
                        "id": employee.pk,
                        "site": (
                            {
                                "id": employee.work_site_id,
                                "name": employee.work_site.name,
                                "code": employee.work_site.code,
                                "type": employee.work_site.site_type,
                                "parent_id": employee.work_site.parent_id,
                            }
                            if employee.work_site_id
                            else None
                        ),
                        "department": (
                            {
                                "id": employee.department_id,
                                "name": employee.department.name,
                                "code": employee.department.code,
                            }
                            if employee.department_id
                            else None
                        ),
                    }
                    if employee
                    else None
                ),
                "current_shift": (
                    {
                        "id": current_shift.pk,
                        "business_date": current_shift.business_date,
                        "status": current_shift.status,
                        "opened_at": current_shift.opened_at,
                        "site_id": current_shift.site_id,
                        "vehicle": (
                            {
                                "id": current_shift.vehicle_id,
                                "name": current_shift.vehicle.name,
                            }
                            if current_shift.vehicle_id
                            else None
                        ),
                        "opening_cash": current_shift.opening_cash,
                    }
                    if current_shift
                    else None
                ),
            }
        )
