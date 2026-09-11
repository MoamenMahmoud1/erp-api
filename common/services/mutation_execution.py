from dataclasses import dataclass
from typing import Any, Callable

from common.exceptions import InvalidBusinessOperation
from common.services.approval_requests import request_approval
from common.services.mutation_authorization import MutationAuthorizationService, MutationDecision


@dataclass(frozen=True)
class MutationExecutionResult:
    decision: MutationDecision
    result: Any


class MutationExecutionService:
    """Execute an authorized mutation directly or turn it into an approval request."""

    @classmethod
    def execute(
        cls,
        *,
        actor,
        resource: str,
        action: str,
        direct_permission: str,
        direct_operation: Callable[[], Any],
        target_id: int,
        payload: dict | None = None,
        reason: str = "",
        idempotency_key: str | None = None,
        path: str = "/api/v1/approvals/",
    ) -> MutationExecutionResult:
        decision = MutationAuthorizationService.decide(
            actor=actor,
            resource=resource,
            action=action,
            direct_permission=direct_permission,
        )

        if decision.decision is MutationDecision.DIRECT:
            return MutationExecutionResult(
                decision=decision.decision,
                result=direct_operation(),
            )

        if decision.decision is MutationDecision.REQUEST_APPROVAL:
            approval_result = request_approval(
                requester=actor,
                target_type=resource,
                target_id=target_id,
                operation=action,
                payload=payload or {},
                reason=reason,
                idempotency_key=idempotency_key,
                path=path,
            )
            return MutationExecutionResult(
                decision=decision.decision,
                result=approval_result,
            )

        raise InvalidBusinessOperation(decision.reason or "This operation is not permitted.")
