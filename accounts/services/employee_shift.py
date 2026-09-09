from decimal import Decimal

from django.db import transaction
from django.db.models import Sum
from django.db.models.functions import Coalesce
from django.utils import timezone

from auditlog.services import record_event
from common.exceptions import InvalidBusinessOperation
from common.money import quantize_money
from inventory.models import StockLocation
from organization.models import Site

from accounts.models import Employee, EmployeeShift, Role
from services.organization_scope import visible_site_ids


class ShiftError(InvalidBusinessOperation):
    pass


def employee_for_user(user, *, required=True):
    employee = Employee.objects.select_related("user", "work_site").filter(user_id=user.pk).first()
    if employee is None and required:
        raise ShiftError("The authenticated user is not assigned to an employee record.")
    return employee


def current_shift_for_user(user):
    if not user or not getattr(user, "is_authenticated", False):
        return None
    return (
        EmployeeShift.objects.select_related("site", "vehicle", "employee__user")
        .filter(employee__user_id=user.pk, status=EmployeeShift.Status.OPEN)
        .first()
    )


def require_open_shift(user):
    """Return the current shift when the actor's role requires one."""
    if not Role.requires_shift_for_user(user):
        return current_shift_for_user(user)
    shift = current_shift_for_user(user)
    if shift is None:
        raise ShiftError("An open shift is required for this operation.")
    return shift


def operation_context(user, *, requested_site=None):
    """Resolve employee, permitted site and optional current shift for a mutation."""
    employee = employee_for_user(user, required=False)
    role_scope = Role.scope_for_user(user)
    shift = current_shift_for_user(user)

    if role_scope == Role.Scope.COMPANY:
        if requested_site is not None:
            site = Site.objects.filter(pk=requested_site.pk, is_active=True).first()
            if site is None:
                raise ShiftError("The selected site is inactive or does not exist.")
        elif shift is not None:
            site = shift.site
        elif employee is not None and employee.work_site_id:
            site = employee.work_site
        else:
            site = None
    else:
        if employee is None or employee.work_site_id is None:
            raise ShiftError("The user must have an employee record and work site.")
        allowed_sites = visible_site_ids(user)
        site = Site.objects.filter(pk=requested_site.pk if requested_site else employee.work_site_id, is_active=True).first()
        if site is None or (allowed_sites is not None and not Site.objects.filter(pk=site.pk).filter(pk__in=allowed_sites).exists()):
            raise ShiftError("The selected site is outside the user's allowed scope.")

    if Role.requires_shift_for_user(user):
        if shift is None:
            raise ShiftError("An open shift is required for this operation.")
        if site is None:
            site = shift.site
        if site.pk != shift.site_id:
            raise ShiftError("The selected site must match the current shift site.")

    return employee, site, shift


@transaction.atomic
def start_shift(*, user, opening_cash=Decimal("0.00"), vehicle_id=None):
    employee = employee_for_user(user)
    if employee.work_site_id is None:
        raise ShiftError("The employee must have a work site before starting a shift.")

    opening_cash = quantize_money(opening_cash)
    if opening_cash < 0:
        raise ShiftError("Opening cash cannot be negative.")

    business_date = timezone.localdate()
    existing = EmployeeShift.objects.select_for_update().filter(employee=employee, business_date=business_date).first()
    if existing is not None:
        if existing.status == EmployeeShift.Status.OPEN:
            raise ShiftError("The employee already has an open shift today.")
        raise ShiftError("The employee already has a closed shift today.")

    vehicle = None
    if vehicle_id is not None:
        vehicle = (
            StockLocation.objects.select_for_update()
            .filter(
                pk=vehicle_id,
                site_id=employee.work_site_id,
                employee_id=employee.user_id,
                location_type=StockLocation.LocationType.SALES_VEHICLE,
                is_active=True,
            )
            .first()
        )
        if vehicle is None:
            raise ShiftError("The selected sales vehicle is not assigned to this employee and site.")

    shift = EmployeeShift.objects.create(
        employee=employee,
        site_id=employee.work_site_id,
        vehicle=vehicle,
        business_date=business_date,
        opening_cash=opening_cash,
        status=EmployeeShift.Status.OPEN,
    )
    record_event(
        action="employee_shift.start",
        entity_type="EmployeeShift",
        entity_id=shift.pk,
        actor_id=user.pk,
        metadata={"employee_id": employee.pk, "site_id": shift.site_id, "vehicle_id": shift.vehicle_id, "business_date": str(shift.business_date)},
    )
    return shift


def _shift_payment_totals(shift):
    from payments.models import PaymentRefund, PaymentTransaction

    collected = PaymentTransaction.objects.filter(shift_id=shift.pk).aggregate(
        cash=Coalesce(Sum("cash_amount"), Decimal("0.00")),
        transfer=Coalesce(Sum("transfer_amount"), Decimal("0.00")),
    )
    refunded = PaymentRefund.objects.filter(shift_id=shift.pk).aggregate(
        cash=Coalesce(Sum("cash_amount"), Decimal("0.00")),
        transfer=Coalesce(Sum("transfer_amount"), Decimal("0.00")),
    )
    return {
        "expected_cash": quantize_money(shift.opening_cash + collected["cash"] - refunded["cash"]),
        "expected_transfer": quantize_money(collected["transfer"] - refunded["transfer"]),
    }


@transaction.atomic
def close_shift(*, user, closing_cash, closing_transfer, notes=""):
    employee = employee_for_user(user)
    try:
        shift = (
            EmployeeShift.objects
            .select_for_update(of=("self",))
            .select_related("site", "vehicle")
            .get(employee=employee, status=EmployeeShift.Status.OPEN)
        )
    except EmployeeShift.DoesNotExist as exc:
        raise ShiftError("There is no open shift for this employee.") from exc

    closing_cash = quantize_money(closing_cash)
    closing_transfer = quantize_money(closing_transfer)
    if closing_cash < 0 or closing_transfer < 0:
        raise ShiftError("Closing amounts cannot be negative.")

    totals = _shift_payment_totals(shift)
    shift.status = EmployeeShift.Status.CLOSED
    shift.closed_at = timezone.now()
    shift.closing_cash = closing_cash
    shift.closing_transfer = closing_transfer
    shift.closing_notes = notes.strip()
    shift.save(update_fields=("status", "closed_at", "closing_cash", "closing_transfer", "closing_notes", "updated_at"))

    record_event(
        action="employee_shift.close",
        entity_type="EmployeeShift",
        entity_id=shift.pk,
        actor_id=user.pk,
        metadata={
            "employee_id": employee.pk,
            "site_id": shift.site_id,
            "vehicle_id": shift.vehicle_id,
            "expected_cash": str(totals["expected_cash"]),
            "actual_cash": str(closing_cash),
            "cash_difference": str(quantize_money(closing_cash - totals["expected_cash"])),
            "expected_transfer": str(totals["expected_transfer"]),
            "actual_transfer": str(closing_transfer),
            "transfer_difference": str(quantize_money(closing_transfer - totals["expected_transfer"])),
        },
    )
    return shift, totals
