"""Business permissions for payment operations."""

from rest_framework.permissions import BasePermission


class CollectionPermission(BasePermission):
    def has_permission(self, request, view):
        user = request.user
        return bool(
            user
            and user.is_authenticated
            and (user.is_staff or user.is_superuser or user.has_perm("payments.process_collection"))
        )


class RefundPermission(BasePermission):
    def has_permission(self, request, view):
        user = request.user
        return bool(
            user
            and user.is_authenticated
            and (user.is_staff or user.is_superuser or user.has_perm("payments.refund_payment"))
        )


class TransactionReadPermission(BasePermission):
    def has_permission(self, request, view):
        user = request.user
        return bool(
            user
            and user.is_authenticated
            and (user.is_staff or user.is_superuser or user.has_perm("payments.view_paymenttransaction"))
        )
