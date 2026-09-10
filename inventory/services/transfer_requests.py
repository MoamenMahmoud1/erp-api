from django.db import transaction
from django.utils import timezone

from accounts.services.employee_shift import require_open_shift
from common.exceptions import InvalidBusinessOperation
from inventory.models import StockLocation, StockMovement, StockTransferRequest, StockTransferRequestItem
from inventory.services.transfer_stock import TransferStock
from invoices.services.returns import create_sales_return


class StockTransferRequestError(InvalidBusinessOperation):
    pass


def _warehouse_for_request(*, warehouse_id, requested_by):
    warehouse = (
        StockLocation.objects
        .filter(
            pk=warehouse_id,
            location_type=StockLocation.LocationType.MAIN_WAREHOUSE,
            is_active=True,
        )
        .prefetch_related("warehouse_managers")
        .first()
    )
    if warehouse is None:
        raise StockTransferRequestError("The selected warehouse is not active or does not exist.")

    employee = getattr(requested_by, "employee", None)
    if employee is not None and employee.work_site_id and warehouse.site_id != employee.work_site_id:
        raise StockTransferRequestError("The selected warehouse is outside the representative's work site.")
    return warehouse


def _validate_warehouse_manager(*, warehouse, manager, requested_by):
    if manager is None or not manager.is_active:
        raise StockTransferRequestError("The selected warehouse manager is invalid.")
    if manager.pk == requested_by.pk:
        raise StockTransferRequestError("The representative cannot approve their own stock request.")
    if not warehouse.warehouse_managers.filter(pk=manager.pk).exists():
        raise StockTransferRequestError("The selected user is not assigned as a manager for this warehouse.")
    if not manager.is_superuser and not manager.has_perm("inventory.approve_stock_transfer"):
        raise StockTransferRequestError("The selected warehouse manager is not authorized to approve stock requests.")

    employee = getattr(manager, "employee", None)
    if employee is not None and warehouse.site_id and employee.work_site_id != warehouse.site_id:
        raise StockTransferRequestError("The warehouse manager must belong to the warehouse site.")


def _get_shift_for_request(requested_by):
    try:
        shift = require_open_shift(requested_by)
    except InvalidBusinessOperation as exc:
        raise StockTransferRequestError(str(exc)) from exc
    if shift is None or shift.vehicle_id is None:
        raise StockTransferRequestError("An open shift with an assigned vehicle is required.")
    return shift


@transaction.atomic
def create_stock_transfer_request(*, requested_by, request_type, warehouse_id, warehouse_manager_id, items, invoice_id=None, reference=""):
    shift = _get_shift_for_request(requested_by)
    warehouse = _warehouse_for_request(warehouse_id=warehouse_id, requested_by=requested_by)
    manager = warehouse.warehouse_managers.filter(pk=warehouse_manager_id).first()
    _validate_warehouse_manager(warehouse=warehouse, manager=manager, requested_by=requested_by)

    if request_type == StockTransferRequest.RequestType.WAREHOUSE_TO_VEHICLE:
        source_location = warehouse
        destination_location = shift.vehicle
        if invoice_id is not None:
            raise StockTransferRequestError("A loading request cannot be linked to an invoice return.")
    elif request_type == StockTransferRequest.RequestType.VEHICLE_TO_WAREHOUSE:
        source_location = shift.vehicle
        destination_location = warehouse
        if invoice_id is None:
            raise StockTransferRequestError("A return request must reference the customer invoice.")
    else:
        raise StockTransferRequestError("Unsupported stock transfer request type.")

    if destination_location.site_id != warehouse.site_id or source_location.site_id != warehouse.site_id:
        raise StockTransferRequestError("The warehouse and vehicle must belong to the same site.")

    if not items:
        raise StockTransferRequestError("A stock request must contain at least one item.")

    if request_type == StockTransferRequest.RequestType.VEHICLE_TO_WAREHOUSE:
        from invoices.models import Invoice

        invoice = Invoice.objects.visible_to(requested_by).filter(pk=invoice_id).first()
        if invoice is None:
            raise StockTransferRequestError("The selected invoice is not accessible.")
        if invoice.shift_id != shift.pk:
            raise StockTransferRequestError("The return invoice must belong to the current shift.")
        if invoice.created_by_id != requested_by.pk:
            raise StockTransferRequestError("The return invoice must belong to the requesting representative.")

    request = StockTransferRequest.objects.create(
        request_type=request_type,
        requested_by=requested_by,
        warehouse_manager=manager,
        shift=shift,
        warehouse=warehouse,
        source_location=source_location,
        destination_location=destination_location,
        reference=reference.strip(),
    )

    for item in items:
        StockTransferRequestItem.objects.create(
            request=request,
            product=item["product"],
            quantity=item["quantity"],
            invoice_item=item.get("invoice_item"),
        )

    return request


@transaction.atomic
def approve_stock_transfer_request(*, request_id, approver):
    request = (
        StockTransferRequest.objects
        .select_for_update()
        .select_related("requested_by", "warehouse_manager", "shift", "warehouse", "source_location", "destination_location")
        .prefetch_related("items__product", "items__invoice_item")
        .get(pk=request_id)
    )
    if request.status != StockTransferRequest.Status.PENDING:
        raise StockTransferRequestError("Only pending stock requests can be approved.")
    if request.warehouse_manager_id != approver.pk:
        raise StockTransferRequestError("Only the selected warehouse manager can approve this request.")
    if not approver.is_superuser and not approver.has_perm("inventory.approve_stock_transfer"):
        raise StockTransferRequestError("You are not authorized to approve stock requests.")

    if request.request_type == StockTransferRequest.RequestType.WAREHOUSE_TO_VEHICLE:
        movement = TransferStock()(
            source_id=request.source_location_id,
            destination_id=request.destination_location_id,
            items=[{"product": item.product, "quantity": item.quantity} for item in request.items.all()],
            created_by=approver,
            reference=f"Stock Request #{request.pk}",
            shift=request.shift,
        )
        request.approved_movement = movement
    else:
        item_invoice_ids = {item.invoice_item.invoice_id for item in request.items.all() if item.invoice_item_id}
        if len(item_invoice_ids) != 1:
            raise StockTransferRequestError("A return request must reference exactly one invoice.")
        invoice_id = next(iter(item_invoice_ids))

        sales_return = create_sales_return(
            invoice_id=invoice_id,
            items=[{"invoice_item": item.invoice_item, "quantity": item.quantity} for item in request.items.all()],
            created_by_id=request.requested_by_id,
            reason=request.reference or f"Approved return request #{request.pk}",
            actor=request.requested_by,
            processing_shift=request.shift,
            return_source_location_id=request.source_location_id,
            return_destination_location_id=request.destination_location_id,
        )
        request.invoice_return = sales_return

    request.status = StockTransferRequest.Status.APPROVED
    request.approved_by = approver
    request.reviewed_at = timezone.now()
    request.rejection_reason = ""
    request.save(update_fields=("status", "approved_by", "reviewed_at", "approved_movement", "invoice_return", "rejection_reason"))
    return request


@transaction.atomic
def reject_stock_transfer_request(*, request_id, approver, reason=""):
    request = StockTransferRequest.objects.select_for_update().select_related("warehouse_manager").get(pk=request_id)
    if request.status != StockTransferRequest.Status.PENDING:
        raise StockTransferRequestError("Only pending stock requests can be rejected.")
    if request.warehouse_manager_id != approver.pk:
        raise StockTransferRequestError("Only the selected warehouse manager can reject this request.")
    if not approver.is_superuser and not approver.has_perm("inventory.approve_stock_transfer"):
        raise StockTransferRequestError("You are not authorized to reject stock requests.")

    request.status = StockTransferRequest.Status.REJECTED
    request.approved_by = approver
    request.reviewed_at = timezone.now()
    request.rejection_reason = reason.strip()
    request.save(update_fields=("status", "approved_by", "reviewed_at", "rejection_reason"))
    return request
