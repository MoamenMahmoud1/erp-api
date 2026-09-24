from uuid import uuid4

from django.db import transaction
from django.utils import timezone

from accounts.models import Employee, RoleProfile
from auditlog.models import AuditEvent
from common.exceptions import InvalidBusinessOperation
from common.idempotency import IdempotentResult, execute_idempotent
from customers.models import Customer
from inventory.models import StockBalance, StockLocation
from invoices.models import Invoice
from invoices.services import DeleteInvoice, UpdateInvoice
from notifications.services import queue_approval_event_notification
from products.models import Product


REQUESTED_ACTION = "approval.requested"
APPROVED_ACTION = "approval.approved"
REJECTED_ACTION = "approval.rejected"


def _manager_for_user(user):
    employee = (
        Employee.objects
        .select_related("manager__user")
        .filter(user_id=user.pk)
        .first()
    )
    if employee is None or employee.manager is None:
        raise InvalidBusinessOperation("The requester does not have a direct manager assigned.")
    manager = employee.manager.user
    if not RoleProfile.can_manage_user(manager, user):
        raise InvalidBusinessOperation("The assigned manager must have a higher role level than the requester.")
    return manager


def _event_payload(event, status_override=None):
    metadata = event.metadata or {}
    return {
        "id": event.pk,
        "status": status_override or metadata.get("status", "pending"),
        "target_type": event.entity_type,
        "target_id": event.entity_id,
        "operation": metadata.get("operation"),
        "requested_by": event.actor_id,
        "approver": metadata.get("approver_id"),
        "payload": metadata.get("payload", {}),
        "reason": metadata.get("reason", ""),
        "decision_reason": metadata.get("decision_reason", ""),
        "created_at": event.created_at.isoformat(),
        "reviewed_at": metadata.get("reviewed_at"),
    }


def _decision_exists(approval_event_id):
    return AuditEvent.objects.filter(
        action__in=(APPROVED_ACTION, REJECTED_ACTION),
        metadata__approval_id=approval_event_id,
    ).exists()


def _load_request_for_update(approval_event_id):
    event = (
        AuditEvent.objects
        .select_for_update()
        .filter(pk=approval_event_id, action=REQUESTED_ACTION)
        .first()
    )
    if event is None:
        raise InvalidBusinessOperation("Approval request not found.")
    if _decision_exists(event.pk):
        raise InvalidBusinessOperation("This approval request has already been reviewed.")
    return event


def _validate_create_request(*, requester, target_type, target_id, operation, payload):
    if operation not in {"update", "delete"}:
        raise InvalidBusinessOperation("Only update and delete approval requests are supported.")

    manager = _manager_for_user(requester)
    normalized_payload = payload or {}

    if target_type == "invoice":
        invoice = (
            Invoice.objects.visible_to(requester)
            .select_related("created_by", "customer")
            .filter(pk=target_id, created_by_id=requester.pk)
            .first()
        )
        if invoice is None:
            raise InvalidBusinessOperation("Invoice not found or not owned by the requester.")
        if invoice.status != Invoice.Status.DRAFT:
            raise InvalidBusinessOperation("Only draft invoices can be changed through manager approval.")
        if operation == "update":
            try:
                customer_id = int(normalized_payload.get("customer", invoice.customer_id))
            except (TypeError, ValueError):
                raise InvalidBusinessOperation("Invalid customer id.")
            customer = Customer.objects.filter(pk=customer_id).first()
            if customer is None:
                raise InvalidBusinessOperation("Customer not found.")
            raw_items = normalized_payload.get("items")
            if not isinstance(raw_items, list) or not raw_items:
                raise InvalidBusinessOperation("An invoice update must contain at least one item.")
            product_ids = []
            items = []
            for raw in raw_items:
                if not isinstance(raw, dict):
                    raise InvalidBusinessOperation("Invalid invoice item payload.")
                try:
                    product_id = int(raw.get("product", 0))
                    quantity = int(raw.get("quantity", 0))
                except (TypeError, ValueError):
                    raise InvalidBusinessOperation("Invalid invoice item values.")
                product_ids.append(product_id)
                items.append({"product": product_id, "quantity": quantity})
            if len(product_ids) != len(set(product_ids)) or any(item["quantity"] <= 0 for item in items):
                raise InvalidBusinessOperation("Invoice items must use unique positive quantities.")
            products = {p.pk: p for p in Product.objects.active().filter(pk__in=product_ids)}
            if len(products) != len(product_ids):
                raise InvalidBusinessOperation("Every invoice product must exist and be active.")
            normalized_payload = {
                "customer": customer.pk,
                "items": [
                    {"product": products[item["product"]].pk, "quantity": item["quantity"]}
                    for item in items
                ],
            }
        else:
            if invoice.net_paid_amount > 0:
                raise InvalidBusinessOperation("A paid invoice cannot be deleted.")
            normalized_payload = {}

    elif target_type == "vehicle":
        vehicle = (
            StockLocation.objects
            .filter(
                pk=target_id,
                location_type=StockLocation.LocationType.SALES_VEHICLE,
                employee_id=requester.pk,
            )
            .first()
        )
        if vehicle is None:
            raise InvalidBusinessOperation("Vehicle not found or not owned by the requester.")
        if operation == "update":
            unknown = set(normalized_payload) - {"name"}
            if unknown:
                raise InvalidBusinessOperation("Only the vehicle name can be changed by an approval request.")
            name = str(normalized_payload.get("name", "")).strip()
            if not name or len(name) > 150:
                raise InvalidBusinessOperation("Vehicle name must be between 1 and 150 characters.")
            normalized_payload = {"name": name}
        else:
            if StockBalance.objects.filter(location=vehicle, quantity__gt=0).exists():
                raise InvalidBusinessOperation("A vehicle with remaining stock cannot be deactivated.")
            normalized_payload = {}
    else:
        raise InvalidBusinessOperation("Unsupported approval target.")

    return manager, normalized_payload


def _has_duplicate_pending_request(*, requester_id, target_type, target_id, operation):
    for event in AuditEvent.objects.filter(
        action=REQUESTED_ACTION,
        actor_id=requester_id,
        entity_type=target_type,
        entity_id=target_id,
        metadata__operation=operation,
    ).only("id"):
        if not _decision_exists(event.pk):
            return event
    return None


def request_approval(*, requester, target_type, target_id, operation, payload=None, reason="", idempotency_key=None, path="/api/v1/approvals/"):
    if not idempotency_key:
        raise InvalidBusinessOperation("Idempotency-Key is required.")

    raw_payload = payload or {}
    raw_data = {
        "target_type": target_type,
        "target_id": int(target_id),
        "operation": operation,
        "payload": raw_payload,
        "reason": str(reason or "").strip(),
    }

    @transaction.atomic
    def create():
        manager, normalized_payload = _validate_create_request(
            requester=requester,
            target_type=target_type,
            target_id=target_id,
            operation=operation,
            payload=raw_payload,
        )
        duplicate = _has_duplicate_pending_request(
            requester_id=requester.pk,
            target_type=target_type,
            target_id=target_id,
            operation=operation,
        )
        if duplicate is not None:
            return IdempotentResult(status=200, body=_event_payload(duplicate))

        event = AuditEvent.objects.create(
            action=REQUESTED_ACTION,
            entity_type=target_type,
            entity_id=target_id,
            actor_id=requester.pk,
            request_id=idempotency_key,
            metadata={
                "approval_id": str(uuid4()),
                "operation": operation,
                "approver_id": manager.pk,
                "payload": normalized_payload,
                "reason": raw_data["reason"],
                "status": "pending",
            },
        )
        queue_approval_event_notification(event)
        return IdempotentResult(status=201, body=_event_payload(event))

    return execute_idempotent(
        key=idempotency_key,
        user_id=requester.pk,
        path=path,
        data=raw_data,
        operation=create,
    )


def review_approval(*, approver, approval_event_id, decision, reason="", idempotency_key=None, path_prefix="/api/v1/approvals/"):
    if decision not in {"approve", "reject"}:
        raise InvalidBusinessOperation("Unsupported approval decision.")
    if not idempotency_key:
        raise InvalidBusinessOperation("Idempotency-Key is required.")

    @transaction.atomic
    def review():
        request_event = _load_request_for_update(approval_event_id)
        metadata = request_event.metadata or {}
        requester_id = request_event.actor_id
        target_type = request_event.entity_type
        target_id = request_event.entity_id
        operation = metadata.get("operation")
        payload = metadata.get("payload") or {}
        assigned_approver_id = metadata.get("approver_id")

        if assigned_approver_id != approver.pk:
            raise InvalidBusinessOperation("Only the requester’s assigned manager can review this request.")
        requester = Employee.objects.select_related("manager__user").filter(user_id=requester_id).first()
        if requester is None or requester.manager is None or requester.manager.user_id != approver.pk:
            raise InvalidBusinessOperation("The approval is no longer assigned to this manager.")
        if not RoleProfile.can_manage_user(approver, requester.user):
            raise InvalidBusinessOperation("Approval requires a higher role level than the requester.")

        if decision == "approve":
            if target_type == "invoice":
                invoice = Invoice.objects.filter(pk=target_id).first()
                if invoice is None:
                    raise InvalidBusinessOperation("Invoice no longer exists.")
                if operation == "update":
                    customer = Customer.objects.filter(pk=int(payload["customer"])).first()
                    if customer is None:
                        raise InvalidBusinessOperation("Requested customer no longer exists.")
                    raw_items = payload.get("items") or []
                    product_ids = [int(item["product"]) for item in raw_items]
                    products = {p.pk: p for p in Product.objects.active().filter(pk__in=product_ids)}
                    if len(products) != len(product_ids):
                        raise InvalidBusinessOperation("One or more requested products are no longer active.")
                    validated = {
                        "customer": customer,
                        "items": [
                            {"product": products[int(item["product"])], "quantity": int(item["quantity"])}
                            for item in raw_items
                        ],
                    }
                    result = UpdateInvoice()(invoice_id=target_id, validated_data=validated, actor=approver)
                    body = {"invoice": result.pk, "operation": "update", "status": "approved"}
                elif operation == "delete":
                    DeleteInvoice()(invoice_id=target_id, actor=approver)
                    body = {"invoice": target_id, "operation": "delete", "status": "approved"}
                else:
                    raise InvalidBusinessOperation("Unsupported invoice approval operation.")
            elif target_type == "vehicle":
                vehicle = StockLocation.objects.filter(
                    pk=target_id,
                    location_type=StockLocation.LocationType.SALES_VEHICLE,
                    employee_id=requester_id,
                ).select_for_update().first()
                if vehicle is None:
                    raise InvalidBusinessOperation("Vehicle no longer exists or is no longer assigned to the requester.")
                if operation == "update":
                    vehicle.name = str(payload["name"]).strip()
                    vehicle.save(update_fields=("name", "updated_at") if hasattr(vehicle, "updated_at") else ("name",))
                    body = {"vehicle": vehicle.pk, "operation": "update", "status": "approved"}
                elif operation == "delete":
                    if StockBalance.objects.filter(location=vehicle, quantity__gt=0).exists():
                        raise InvalidBusinessOperation("A vehicle with remaining stock cannot be deactivated.")
                    vehicle.is_active = False
                    vehicle.save(update_fields=("is_active",))
                    body = {"vehicle": vehicle.pk, "operation": "delete", "status": "approved"}
                else:
                    raise InvalidBusinessOperation("Unsupported vehicle approval operation.")
            else:
                raise InvalidBusinessOperation("Unsupported approval target.")
        else:
            body = {"target_type": target_type, "target_id": target_id, "operation": operation, "status": "rejected"}

        decision_event = AuditEvent.objects.create(
            action=APPROVED_ACTION if decision == "approve" else REJECTED_ACTION,
            entity_type=target_type,
            entity_id=target_id,
            actor_id=approver.pk,
            request_id=idempotency_key,
            metadata={
                "approval_id": request_event.pk,
                "request_event_id": request_event.pk,
                "requester_id": requester_id,
                "operation": operation,
                "decision_reason": str(reason or "").strip(),
                "reviewed_at": timezone.now().isoformat(),
                "status": "approved" if decision == "approve" else "rejected",
            },
        )
        queue_approval_event_notification(decision_event)
        body["approval_request_id"] = request_event.pk
        body["decision_event_id"] = decision_event.pk
        return IdempotentResult(status=200, body=body)

    return execute_idempotent(
        key=idempotency_key,
        user_id=approver.pk,
        path=f"{path_prefix}{approval_event_id}/{decision}/",
        data={
            "approval_event_id": int(approval_event_id),
            "decision": decision,
            "reason": str(reason or "").strip(),
        },
        operation=review,
    )


def list_pending_for_manager(*, manager, limit=100):
    events = list(
        AuditEvent.objects
        .filter(action=REQUESTED_ACTION, metadata__approver_id=manager.pk)
        .order_by("-created_at", "-id")[:limit]
    )
    decisions = AuditEvent.objects.filter(
        action__in=(APPROVED_ACTION, REJECTED_ACTION),
        metadata__approval_id__in=[event.pk for event in events],
    ).values_list("metadata__approval_id", "action")
    decision_by_id = {int(request_id): action for request_id, action in decisions if request_id is not None}
    return [
        _event_payload(event)
        for event in events
        if event.pk not in decision_by_id
    ]
