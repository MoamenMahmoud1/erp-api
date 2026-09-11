from accounts.models import RoleProfile
from common.exceptions import InvalidBusinessOperation
from customers.models import Customer

from .models import CustomerAssignment


def assigned_customer_queryset(user):
    """Return the customer set visible to a shift-bound field representative."""
    queryset = Customer.objects.all()
    if not RoleProfile.requires_shift_for_user(user):
        return queryset

    employee = getattr(user, "employee", None)
    if employee is None:
        return queryset.none()

    return queryset.filter(
        representative_assignments__employee_id=employee.pk,
        representative_assignments__is_active=True,
    ).distinct()


def customer_is_assigned_to_user(customer, user):
    if not RoleProfile.requires_shift_for_user(user):
        return True

    employee = getattr(user, "employee", None)
    if employee is None:
        return False

    customer_id = customer.pk if hasattr(customer, "pk") else customer
    return CustomerAssignment.objects.filter(
        customer_id=customer_id,
        employee_id=employee.pk,
        is_active=True,
    ).exists()


def require_customer_assignment(*, customer, user):
    if not customer_is_assigned_to_user(customer, user):
        raise InvalidBusinessOperation(
            "The selected customer is not assigned to this representative."
        )
