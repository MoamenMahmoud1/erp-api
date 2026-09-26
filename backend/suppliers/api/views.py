from django.db import transaction
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, generics

from suppliers.api.serializers import SupplierSerializer
from suppliers.models import Supplier
from suppliers.permissions.supplier import SupplierAccessPermission


class SupplierListCreateView(generics.ListCreateAPIView):
    serializer_class = SupplierSerializer
    permission_classes = (SupplierAccessPermission,)
    filter_backends = (DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter)
    filterset_fields = ("is_active",)
    search_fields = ("name", "phone", "email", "address")
    ordering_fields = ("name", "created_at", "updated_at")
    ordering = ("name", "pk")

    def get_queryset(self):
        return Supplier.objects.for_list()

    @transaction.atomic
    def perform_create(self, serializer):
        serializer.save()


class SupplierDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = SupplierSerializer
    permission_classes = (SupplierAccessPermission,)

    def get_queryset(self):
        return Supplier.objects.all()

    @transaction.atomic
    def perform_destroy(self, instance):
        instance.delete()
