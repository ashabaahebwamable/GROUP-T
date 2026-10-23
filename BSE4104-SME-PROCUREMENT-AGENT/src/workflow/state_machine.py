"""
Requisition approval state machine (W4-05).

Reviewed and accepted by Azibo Isaac Alinda on 2026-10-15.

Drafted to unblock W4-05; see the AI Engineering Log for the disclosure
entry. Isaac Alinda, as the assigned owner, should
review and take ownership before this is treated as final.

Governing rule (per the plan and the AI Boundary Matrix, Principle 2):
"The implementation contains no automatic approval path at any value, so
autonomous approval is impossible rather than merely prohibited."

State model:
    OPEN -> DRAFT -> PENDING_APPROVAL -> APPROVED
                                     -> REJECTED
                                     -> QUERIED
        -> HALTED (from any active state)

There is no function in this module that can move a requisition directly from
DRAFT to APPROVED, or into APPROVED without a recorded approver_id and
timestamp. That is enforced by the shape of the code, not by convention.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone


def _normalise_flags(flags: list[str] | tuple[str, ...] | None) -> list[str]:
    """Return a clean list of non-empty string flags, preserving order."""
    cleaned: list[str] = []
    for flag in flags or []:
        if flag is None:
            continue
        text = str(flag).strip()
        if text:
            cleaned.append(text)
    return cleaned


VALID_STATES = {
    "OPEN",
    "DRAFT",
    "PENDING_APPROVAL",
    "APPROVED",
    "REJECTED",
    "QUERIED",
    "HALTED",
}
ACTIVE_STATES = {"OPEN", "DRAFT", "PENDING_APPROVAL"}


class IllegalStateTransitionError(Exception):
    """Raised whenever a transition is attempted that the state machine does
    not expose a code path for. This is the mechanism, not just a message:
    there is no function anywhere in this module that performs a DRAFT ->
    APPROVED transition, so attempting it always raises this error."""


class BlockingFlagsUnresolvedError(Exception):
    """Raised when submission for approval is attempted while unresolved
    policy blocking flags remain (e.g. MINIMUM_VALID_QUOTATIONS_NOT_MET,
    EXPIRED_OR_INVALID_QUOTATION:*). EXCLUDED_SUPPLIER:* is informational
    since 12 Oct 2026: the quotation is already left out of the ranking."""


class UnauthorisedActionError(Exception):
    """Raised when an approval decision is attempted by someone who may not
    make it (US-09): a non-approver role, or the person who prepared the
    requisition."""


def _check_approver(
    requisition: "Requisition", approver_id: str, approver_role: str | None
) -> None:
    """US-09: only an approver who did not prepare the requisition may decide."""
    if (approver_role or "").strip().lower() != "approver":
        raise UnauthorisedActionError(
            f"{approver_id!r} has role {approver_role!r}; only an approver may "
            f"approve, reject or query requisition {requisition.requisition_id}."
        )
    if requisition.created_by and approver_id == requisition.created_by:
        raise UnauthorisedActionError(
            f"{approver_id!r} prepared requisition {requisition.requisition_id} "
            "and may not also decide it."
        )


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
        self.state = str(self.state).strip()
        self.policy_flags = _normalise_flags(self.policy_flags)
        self.created_by = (str(self.created_by).strip() if self.created_by is not None else None) or None
        self.decided_by = (str(self.decided_by).strip() if self.decided_by is not None else None) or None
        self.decision_reason = (
            str(self.decision_reason).strip() if self.decision_reason is not None else None
        ) or None
        if self.state not in VALID_STATES:
            raise ValueError(f"Unknown state: {self.state!r}")


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def start_draft(requisition: Requisition) -> Requisition:
    """OPEN -> DRAFT."""
    if requisition.state != "OPEN":
        raise IllegalStateTransitionError(
            f"Cannot start a draft from state {requisition.state!r}; "
            "only OPEN cases may become DRAFT."
        )
    requisition.state = "DRAFT"
    return requisition


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


def approve(
    requisition: Requisition, *, approver_id: str, approver_role: str | None
) -> Requisition:
    """PENDING_APPROVAL -> APPROVED.

    Requires a real approver_id. There is no default, no "system" approver,
    and no way to reach APPROVED from any state other than PENDING_APPROVAL
    (AI Boundary Matrix Principle 2: no automatic approval path at any value).
    The approver must hold the approver role and must not have prepared the
    requisition (US-09); callers look the role up in the user registry.
    """
    if requisition.state != "PENDING_APPROVAL":
        raise IllegalStateTransitionError(
            f"Cannot approve from state {requisition.state!r}; only a "
            "PENDING_APPROVAL requisition may be approved. There is no direct "
            "DRAFT -> APPROVED path."
        )

    if not approver_id or not str(approver_id).strip():
        raise ValueError("approve() requires a non-empty approver_id.")
    _check_approver(requisition, approver_id, approver_role)

    requisition.state = "APPROVED"
    requisition.decided_by = str(approver_id).strip()
    requisition.decided_at = _now_iso()
    requisition.decision_reason = None
    return requisition


def reject(
    requisition: Requisition,
    *,
    approver_id: str,
    approver_role: str | None,
    reason: str,
) -> Requisition:
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
    _check_approver(requisition, approver_id, approver_role)

    requisition.state = "REJECTED"
    requisition.decided_by = str(approver_id).strip()
    requisition.decided_at = _now_iso()
    requisition.decision_reason = str(reason).strip()
    return requisition


def query(
    requisition: Requisition,
    *,
    approver_id: str,
    approver_role: str | None,
    reason: str,
) -> Requisition:
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
    _check_approver(requisition, approver_id, approver_role)

    requisition.state = "QUERIED"
    requisition.decided_by = str(approver_id).strip()
    requisition.decided_at = _now_iso()
    requisition.decision_reason = str(reason).strip()
    return requisition


def halt(requisition: Requisition, *, reason: str) -> Requisition:
    """Move an active case to HALTED. Halted cases cannot be resumed."""
    if requisition.state not in ACTIVE_STATES:
        raise IllegalStateTransitionError(
            f"Cannot halt from state {requisition.state!r}; only active cases "
            "may be halted."
        )
    if not reason or not str(reason).strip():
        raise ValueError("halt() requires a non-empty reason.")

    requisition.state = "HALTED"
    requisition.decided_by = None
    requisition.decided_at = _now_iso()
    requisition.decision_reason = str(reason).strip()
    return requisition


__all__ = [
    "VALID_STATES",
    "ACTIVE_STATES",
    "Requisition",
    "IllegalStateTransitionError",
    "BlockingFlagsUnresolvedError",
    "UnauthorisedActionError",
    "start_draft",
    "submit_for_approval",
    "approve",
    "reject",
    "query",
    "halt",
]
