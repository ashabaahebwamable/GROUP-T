"""
Requisition approval state machine (W4-05).

Drafted to unblock W4-05 while Isaac Alinda (assigned owner) was without his
machine; see the AI Engineering Log for the disclosure entry. Isaac should
review and take ownership before this is treated as final.

Governing rule (per the plan and the AI Boundary Matrix, Principle 2):
"The implementation contains no automatic approval path at any value, so
autonomous approval is impossible rather than merely prohibited."

State model (from knowledge/records/requisitions.csv schema):
    DRAFT -> PENDING_APPROVAL -> APPROVED
                               -> REJECTED
                               -> QUERIED

There is no function in this module that can move a requisition directly from
DRAFT to APPROVED, or into APPROVED without a recorded approver_id and
timestamp. That is enforced by the shape of the code, not by convention.
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


def approve(requisition: Requisition, *, approver_id: str) -> Requisition:
    """PENDING_APPROVAL -> APPROVED.

    Requires a real approver_id. There is no default, no "system" approver,
    and no way to reach APPROVED from any state other than PENDING_APPROVAL
    (AI Boundary Matrix Principle 2: no automatic approval path at any value).
    """
    if requisition.state != "PENDING_APPROVAL":
        raise IllegalStateTransitionError(
            f"Cannot approve from state {requisition.state!r}; only a "
            "PENDING_APPROVAL requisition may be approved. There is no direct "
            "DRAFT -> APPROVED path."
        )

    if not approver_id or not str(approver_id).strip():
        raise ValueError("approve() requires a non-empty approver_id.")

    requisition.state = "APPROVED"
    requisition.decided_by = approver_id
    requisition.decided_at = _now_iso()
    return requisition


def reject(requisition: Requisition, *, approver_id: str, reason: str) -> Requisition:
    """PENDING_APPROVAL -> REJECTED. Requires an approver and a reason."""
    if requisition.state != "PENDING_APPROVAL":
        raise IllegalStateTransitionError(
            f"Cannot reject from state {requisition.state!r}; only a "
            "PENDING_APPROVAL requisition may be rejected."
        )

    if not approver_id or not str(approver_id).strip():
        raise ValueError("reject() requires a non-empty approver_id.")
    if not reason or not str(reason).strip():
        raise ValueError("reject() requires a non-empty reason.")

    requisition.state = "REJECTED"
    requisition.decided_by = approver_id
    requisition.decided_at = _now_iso()
    requisition.decision_reason = reason
    return requisition


def query(requisition: Requisition, *, approver_id: str, reason: str) -> Requisition:
    """PENDING_APPROVAL -> QUERIED. Requires an approver and a reason."""
    if requisition.state != "PENDING_APPROVAL":
        raise IllegalStateTransitionError(
            f"Cannot query from state {requisition.state!r}; only a "
            "PENDING_APPROVAL requisition may be queried."
        )

    if not approver_id or not str(approver_id).strip():
        raise ValueError("query() requires a non-empty approver_id.")
    if not reason or not str(reason).strip():
        raise ValueError("query() requires a non-empty reason.")

    requisition.state = "QUERIED"
    requisition.decided_by = approver_id
    requisition.decided_at = _now_iso()
    requisition.decision_reason = reason
    return requisition


__all__ = [
    "VALID_STATES",
    "Requisition",
    "IllegalStateTransitionError",
    "BlockingFlagsUnresolvedError",
    "submit_for_approval",
    "approve",
    "reject",
    "query",
]
