from django.db import transaction
from rest_framework import status, viewsets
from rest_framework.response import Response

from common.exceptions import InvalidBusinessOperation
from common.permissions import ReadAuthenticatedWriteStaffPermission
from customers.api.serializers import CustomerSerializer
from customers.models import Customer
from customers.services import DeleteCustomer


class CustomerViewSet(viewsets.ModelViewSet):
    queryset = Customer.objects.all()
    serializer_class = CustomerSerializer
    permission_classes = (ReadAuthenticatedWriteStaffPermission,)

    @transaction.atomic
    def perform_create(self, serializer):
        serializer.save()

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        try:
            DeleteCustomer()(instance=instance)
        except InvalidBusinessOperation as exc:
            return Response(
                {"detail": str(exc), "code": "customer_in_use"},
                status=status.HTTP_409_CONFLICT,
            )
        return Response(status=status.HTTP_204_NO_CONTENT)
