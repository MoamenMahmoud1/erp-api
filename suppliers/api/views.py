from adrf import generics

from suppliers.api.serializers import SupplierSerializer
from suppliers.models import Supplier
from suppliers.permissions.supplier import SupplierAccessPermission


class SupplierListCreateView(generics.ListCreateAPIView):
    serializer_class = SupplierSerializer
    permission_classes = (SupplierAccessPermission,)

    def get_queryset(self):
        return Supplier.objects.for_list()


class SupplierDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = SupplierSerializer
    permission_classes = (SupplierAccessPermission,)

    def get_queryset(self):
        return Supplier.objects.all()
