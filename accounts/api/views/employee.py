from django.contrib.auth import get_user_model
from django.db.models import IntegerField, OuterRef, Q, Subquery, Value
from django.db.models.functions import Coalesce
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from accounts.api.serializers import EmployeeSerializer
from accounts.models import Employee, Role
from accounts.permissions import EmployeeAccessPermission
from common.pagination import StandardPagination


User = get_user_model()


class EmployeeViewSet(viewsets.ModelViewSet):
    serializer_class = EmployeeSerializer
    permission_classes = (EmployeeAccessPermission,)
    pagination_class = StandardPagination
    filter_backends = (DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter)
    filterset_fields = ("work_site", "department", "manager")
    search_fields = (
        "user__username",
        "user__email",
        "user__first_name",
        "user__last_name",
    )
    ordering_fields = ("user__username", "user__first_name", "created_at", "updated_at")
    ordering = ("user__username", "pk")

    def get_queryset(self):
        return (
            Employee.objects.visible_to(
                self.request.user,
                role_level=getattr(self.request, "_employee_role_level", None),
            )
            .select_related(
                "user",
                "manager",
                "manager__user",
                "work_site",
                "department",
            )
            .order_by(*self.ordering)
        )

    @action(detail=False, methods=("get",), url_path="options")
    def options(self, request):
        """Return assignable users for the employee form without trusting client-supplied IDs."""
        users = User.objects.filter(
            is_active=True,
            employee__isnull=True,
        )

        if not request.user.is_superuser:
            actor_level = Role.level_for_user(request.user)
            target_role_level = Subquery(
                Role.objects.filter(group__user=OuterRef("pk"))
                .order_by("-level")
                .values("level")[:1],
                output_field=IntegerField(),
            )
            users = (
                users.filter(is_superuser=False)
                .annotate(_role_level=Coalesce(target_role_level, Value(0)))
                .filter(_role_level__lt=actor_level)
            )

        search = request.query_params.get("search", "").strip()
        if search:
            users = users.filter(
                Q(username__icontains=search)
                | Q(email__icontains=search)
                | Q(first_name__icontains=search)
                | Q(last_name__icontains=search)
            )

        users = users.order_by("first_name", "last_name", "username", "pk")
        page = self.paginate_queryset(users)
        rows = page if page is not None else users
        data = [
            {
                "id": user.pk,
                "username": user.username,
                "email": user.email,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "is_staff": user.is_staff,
            }
            for user in rows
        ]
        if page is not None:
            return self.get_paginated_response(data)
        return Response(data, status=status.HTTP_200_OK)
