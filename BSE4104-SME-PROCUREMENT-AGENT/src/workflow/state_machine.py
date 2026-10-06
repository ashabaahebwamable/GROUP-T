"""Deterministic requisition approval state machine (W4-05).

Only a caller identified as an approver may decide a pending requisition, and
the requisition preparer may not approve their own work. Authorization
failures and decisions are captured as audit events for the persistence layer.

State model::

    DRAFT -> PENDING_APPROVAL -> APPROVED | REJECTED | QUERIED

There is no direct DRAFT -> APPROVED path or automatic approval path at any
value (AI Boundary Matrix, Principle 2).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


VALID_STATES = {"DRAFT", "PENDING_APPROVAL", "APPROVED", "REJECTED", "QUERIED"}


class IllegalStateTransitionError(Exception):
    """Raised whenever a transition is attempted that the state machine does
    not expose a code path for. This is the mechanism, not just a message:
    there is no function anywhere in this module that performs a DRAFT ->
    APPROVED transition, so attempting it always raises this error."""


class UnauthorizedApproverError(PermissionError):
    """Raised and audited when a non-approver or preparer attempts a decision."""


class BlockingFlagsUnresolvedError(Exception):
    """Raised when submission for approval is attempted while unresolved
    policy blocking flags remain (e.g. MINIMUM_VALID_QUOTATIONS_NOT_MET,
    EXCLUDED_SUPPLIER:*, EXPIRED_OR_INVALID_QUOTATION:*)."""


@dataclass
class Requisition:
    """In-memory representation of one requisition's workflow state.

    A real integration would load/save this from requisitions.csv; this
    class only owns the state transitions themselves, kept separate from
    storage so it can be tested without touching the filesystem.
    """

    requisition_id: str
    state: str = "DRAFT"
    policy_flags: list[str] = field(default_factory=list)
    created_by: str | None = None
    created_at: str | None = None
    decided_by: str | None = None
    decided_at: str | None = None
    decision_reason: str | None = None
    audit_events: list[dict[str, Any]] = field(default_factory=list)

    def __post_init__(self) -> None:
        if self.state not in VALID_STATES:
            raise ValueError(f"Unknown state: {self.state!r}")


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def submit_for_approval(requisition: Requisition) -> Requisition:
    """DRAFT -> PENDING_APPROVAL.

    Refuses the transition while any blocking flag is unresolved (W4-05
    subtask: "submission refused while a blocking flag is unresolved,
    US-07 AC3"). This is the ONLY function that can move a requisition out
    of DRAFT.
    """
    if requisition.state != "DRAFT":
        raise IllegalStateTransitionError(
            f"Cannot submit for approval from state {requisition.state!r}; "
            "only DRAFT requisitions may be submitted."
        )

    if requisition.policy_flags:
        raise BlockingFlagsUnresolvedError(
            f"Requisition {requisition.requisition_id} has unresolved blocking "
            f"flags: {requisition.policy_flags}. Submission refused."
        )

    requisition.state = "PENDING_APPROVAL"
    return requisition


def _record_decision_event(
    requisition: Requisition,
    *,
    action: str,
    actor_id: str,
    actor_role: str,
    outcome: str,
    from_state: str,
    to_state: str | None,
    reason: str | None = None,
) -> None:
    event: dict[str, Any] = {
        "action": action,
        "actor_id": actor_id,
        "actor_role": actor_role,
        "outcome": outcome,
        "from_state": from_state,
        "to_state": to_state,
        "timestamp": _now_iso(),
    }
    if reason is not None:
        event["reason"] = reason
    requisition.audit_events.append(event)


def _require_authorized_approver(
    requisition: Requisition,
    *,
    approver_id: str,
    approver_role: str | None,
    action: str,
) -> None:
    role = str(approver_role or "").strip().casefold()
    actor_id = str(approver_id or "").strip()
    if role != "approver":
        reason = "Only an approver account may make a requisition decision."
        _record_decision_event(
            requisition,
            action=action,
            actor_id=actor_id,
            actor_role=role,
            outcome="denied",
            from_state=requisition.state,
            to_state=None,
            reason=reason,
        )
        raise UnauthorizedApproverError(reason)

    if not actor_id:
        raise ValueError(f"{action}() requires a non-empty approver_id.")

    if (
        action == "approve"
        and requisition.created_by
        and actor_id == requisition.created_by.strip()
    ):
        reason = "The officer who prepared a requisition cannot approve their own work."
        _record_decision_event(
            requisition,
            action=action,
            actor_id=actor_id,
            actor_role=role,
            outcome="denied",
            from_state=requisition.state,
            to_state=None,
            reason=reason,
        )
        raise UnauthorizedApproverError(reason)


def approve(
    requisition: Requisition,
    *,
    approver_id: str,
    approver_role: str | None = None,
) -> Requisition:
    """PENDING_APPROVAL -> APPROVED.

    Requires an authenticated approver role and a real approver_id. The
    preparer cannot approve their own requisition. The role must come from a
    trusted authentication boundary; omitted or non-approver roles fail closed.
    """
    _require_authorized_approver(
        requisition,
        approver_id=approver_id,
        approver_role=approver_role,
        action="approve",
    )
    if requisition.state != "PENDING_APPROVAL":
        raise IllegalStateTransitionError(
            f"Cannot approve from state {requisition.state!r}; only a "
            "PENDING_APPROVAL requisition may be approved. There is no direct "
            "DRAFT -> APPROVED path."
        )

    previous_state = requisition.state
    requisition.state = "APPROVED"
    requisition.decided_by = approver_id
    requisition.decided_at = _now_iso()
    _record_decision_event(
        requisition,
        action="approve",
        actor_id=approver_id,
        actor_role=str(approver_role).strip().casefold(),
        outcome="approved",
        from_state=previous_state,
        to_state=requisition.state,
    )
    return requisition


def reject(
    requisition: Requisition,
    *,
    approver_id: str,
    reason: str,
    approver_role: str | None = None,
) -> Requisition:
    """PENDING_APPROVAL -> REJECTED. Requires an approver and a reason."""
    _require_authorized_approver(
        requisition,
        approver_id=approver_id,
        approver_role=approver_role,
        action="reject",
    )
    if requisition.state != "PENDING_APPROVAL":
        raise IllegalStateTransitionError(
            f"Cannot reject from state {requisition.state!r}; only a "
            "PENDING_APPROVAL requisition may be rejected."
        )

    if not reason or not str(reason).strip():
        raise ValueError("reject() requires a non-empty reason.")

    previous_state = requisition.state
    requisition.state = "REJECTED"
    requisition.decided_by = approver_id
    requisition.decided_at = _now_iso()
    requisition.decision_reason = reason
    _record_decision_event(
        requisition,
        action="reject",
        actor_id=approver_id,
        actor_role=str(approver_role).strip().casefold(),
        outcome="rejected",
        from_state=previous_state,
        to_state=requisition.state,
        reason=reason,
    )
    return requisition


def query(
    requisition: Requisition,
    *,
    approver_id: str,
    reason: str,
    approver_role: str | None = None,
) -> Requisition:
    """PENDING_APPROVAL -> QUERIED. Requires an approver and a reason."""
    _require_authorized_approver(
        requisition,
        approver_id=approver_id,
        approver_role=approver_role,
        action="query",
    )
    if requisition.state != "PENDING_APPROVAL":
        raise IllegalStateTransitionError(
            f"Cannot query from state {requisition.state!r}; only a "
            "PENDING_APPROVAL requisition may be queried."
        )

    if not reason or not str(reason).strip():
        raise ValueError("query() requires a non-empty reason.")

    previous_state = requisition.state
    requisition.state = "QUERIED"
    requisition.decided_by = approver_id
    requisition.decided_at = _now_iso()
    requisition.decision_reason = reason
    _record_decision_event(
        requisition,
        action="query",
        actor_id=approver_id,
        actor_role=str(approver_role).strip().casefold(),
        outcome="queried",
        from_state=previous_state,
        to_state=requisition.state,
        reason=reason,
    )
    return requisition


__all__ = [
    "VALID_STATES",
    "Requisition",
    "IllegalStateTransitionError",
    "UnauthorizedApproverError",
    "BlockingFlagsUnresolvedError",
    "submit_for_approval",
    "approve",
    "reject",
    "query",
]
