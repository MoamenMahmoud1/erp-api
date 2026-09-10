from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.db.models import IntegerField, OuterRef, Q, Subquery, Value
from django.db.models.functions import Coalesce
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from accounts.api.serializers import EmployeeSerializer, GroupSummarySerializer, RoleSummarySerializer, UserSummarySerializer
from accounts.models import Employee, GroupPolicy
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
            .prefetch_related(
                "user__groups__policy",
                "manager__user__groups__policy",
            )
            .order_by(*self.ordering)
        )

    @action(detail=False, methods=("get",), url_path="options")
    def options(self, request):
        """Return assignable users for the employee form without trusting client-supplied IDs."""
        users = User.objects.filter(
            is_active=True,
            employee__isnull=True,
        ).prefetch_related("groups__policy")

        if not request.user.is_superuser:
            actor_level = GroupPolicy.level_for_user(request.user)
            target_role_level = Subquery(
                GroupPolicy.objects.filter(group__user=OuterRef("pk"))
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
        data = UserSummarySerializer(rows, many=True, context={"request": request}).data
        if page is not None:
            return self.get_paginated_response(data)
        return Response(data, status=status.HTTP_200_OK)

    @action(detail=False, methods=("get",), url_path="groups")
    def groups(self, request):
        """Legacy alias: every Django Group is a Role now."""
        groups = Group.objects.select_related("policy").order_by("name", "pk")
        if not request.user.is_superuser:
            groups = groups.annotate(
                _role_level=Coalesce("policy__level", Value(0), output_field=IntegerField())
            ).filter(_role_level__lt=GroupPolicy.level_for_user(request.user))

        search = request.query_params.get("search", "").strip()
        if search:
            groups = groups.filter(
                Q(name__icontains=search)
                | Q(policy__description__icontains=search)
            )

        page = self.paginate_queryset(groups)
        rows = page if page is not None else groups
        data = GroupSummarySerializer(rows, many=True, context={"request": request}).data
        if page is not None:
            return self.get_paginated_response(data)
        return Response(data, status=status.HTTP_200_OK)


class RoleViewSet(viewsets.ReadOnlyModelViewSet):
    """Expose Django Groups directly as ERP roles."""

    serializer_class = RoleSummarySerializer
    permission_classes = (EmployeeAccessPermission,)
    pagination_class = StandardPagination
    filter_backends = (filters.SearchFilter, filters.OrderingFilter)
    search_fields = ("name", "policy__description")

    def get_queryset(self):
        groups = Group.objects.select_related("policy")
        if not self.request.user.is_superuser:
            groups = groups.annotate(
                _role_level=Coalesce("policy__level", Value(0), output_field=IntegerField())
            ).filter(_role_level__lt=GroupPolicy.level_for_user(self.request.user))
        return groups.order_by("name", "pk")
