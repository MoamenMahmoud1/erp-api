from dataclasses import dataclass
from enum import Enum

from accounts.models import Employee, RoleProfile


class MutationDecision(str, Enum):
    DIRECT = "direct"
    REQUEST_APPROVAL = "request_approval"
    DENIED = "denied"


@dataclass(frozen=True)
class MutationAuthorizationDecision:
    decision: MutationDecision
    manager_id: int | None = None
    reason: str = ""


class MutationAuthorizationService:
    """Centralize direct-vs-approval decisions for state-changing actions."""

    APPROVAL_SUPPORTED_ACTIONS = {
        ("invoice", "update"),
        ("invoice", "delete"),
        ("vehicle", "update"),
        ("vehicle", "delete"),
    }

    @classmethod
    def decide(
        cls,
        *,
        actor,
        resource: str,
        action: str,
        direct_permission: str,
    ) -> MutationAuthorizationDecision:
        if not actor or not actor.is_authenticated:
            return MutationAuthorizationDecision(
                MutationDecision.DENIED,
                reason="Authentication is required.",
            )

        has_direct_permission = actor.is_superuser or actor.has_perm(direct_permission)
        approval_supported = (resource, action) in cls.APPROVAL_SUPPORTED_ACTIONS
        approval_required = RoleProfile.requires_shift_for_user(actor)
        manager = cls.approval_manager_for(actor) if approval_supported else None

        if approval_supported and approval_required:
            if manager is None:
                return MutationAuthorizationDecision(
                    MutationDecision.DENIED,
                    reason="This operation requires approval, but no eligible manager is assigned.",
                )
            return MutationAuthorizationDecision(
                MutationDecision.REQUEST_APPROVAL,
                manager_id=manager.pk,
            )

        if has_direct_permission:
            return MutationAuthorizationDecision(MutationDecision.DIRECT)

        return MutationAuthorizationDecision(
            MutationDecision.DENIED,
            reason="The user is not permitted to perform this operation.",
        )

    @staticmethod
    def approval_manager_for(actor):
        employee = (
            Employee.objects
            .select_related("manager__user")
            .filter(user_id=actor.pk)
            .first()
        )
        if employee is None or employee.manager is None:
            return None

        manager = employee.manager.user
        if not RoleProfile.can_manage_user(manager, actor):
            return None
        return manager

    @classmethod
    def can_request_approval(cls, *, actor, resource: str, action: str) -> bool:
        if (resource, action) not in cls.APPROVAL_SUPPORTED_ACTIONS:
            return False
        return cls.approval_manager_for(actor) is not None
