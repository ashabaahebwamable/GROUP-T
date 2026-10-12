"""Persist requisition state changes through the approval state machine.

This is the human-side counterpart to ``create_requisition_draft``: it loads a
requisition from the application-state file, applies one state-machine
transition and writes the result back with an audit event. It is deliberately
NOT registered as a model tool, so the agent can create a DRAFT but can never
submit, approve, reject or query one.
"""

from __future__ import annotations

import csv
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.tools.procurement import AUDIT_LOG_PATH, REQUISITIONS_PATH
from src.workflow.state_machine import (
    Requisition,
    UnauthorisedActionError,
    approve,
    query,
    reject,
    submit_for_approval,
)
from src.workflow.users import role_of


def _parse_flags(value: str | None) -> list[str]:
    text = (value or "").strip()
    if not text:
        return []
    flags = json.loads(text)
    if not isinstance(flags, list):
        raise ValueError("policy_flags must be a JSON list")
    return [str(flag) for flag in flags]


def _read(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open("r", encoding="utf-8-sig", newline="") as source:
        reader = csv.DictReader(source)
        return list(reader.fieldnames or []), list(reader)


def load_requisition(
    requisition_id: str,
    *,
    requisitions_path: Path | str = REQUISITIONS_PATH,
) -> Requisition:
    """Load one requisition row as a state-machine ``Requisition``."""
    _, rows = _read(Path(requisitions_path))
    row = next((row for row in rows if row.get("requisition_id") == requisition_id), None)
    if row is None:
        raise ValueError(f"Unknown requisition: {requisition_id}")
    return Requisition(
        requisition_id=requisition_id,
        state=row.get("state") or "DRAFT",
        policy_flags=_parse_flags(row.get("policy_flags")),
        created_by=row.get("created_by") or None,
        created_at=row.get("created_at") or None,
        decided_by=row.get("decided_by") or None,
        decided_at=row.get("decided_at") or None,
        decision_reason=row.get("decision_reason") or None,
    )


def transition_requisition(
    requisition_id: str,
    action: str,
    *,
    actor_id: str,
    reason: str | None = None,
    requisitions_path: Path | str = REQUISITIONS_PATH,
    audit_log_path: Path | str = AUDIT_LOG_PATH,
    users_path: Path | str | None = None,
) -> dict[str, Any]:
    """Apply a human action (submit, approve, reject, query) and persist it.

    All rules come from ``state_machine``: illegal transitions, unresolved
    blocking flags and missing approver IDs raise before anything is written.
    The actor's role is looked up in the user registry, never taken from the
    caller. An unauthorised decision is refused and the attempt is written to
    the audit log (US-09 criterion 1).
    """
    if not actor_id or not str(actor_id).strip():
        raise ValueError("actor_id is required")

    requisition = load_requisition(requisition_id, requisitions_path=requisitions_path)
    previous_state = requisition.state
    role = role_of(actor_id, users_path=users_path)

    try:
        if action == "submit":
            submit_for_approval(requisition)
        elif action == "approve":
            approve(requisition, approver_id=actor_id, approver_role=role)
        elif action == "reject":
            reject(requisition, approver_id=actor_id, approver_role=role, reason=reason or "")
        elif action == "query":
            query(requisition, approver_id=actor_id, approver_role=role, reason=reason or "")
        else:
            raise ValueError(f"Unknown action: {action!r}")
    except UnauthorisedActionError as exc:
        _append_audit(audit_log_path, {
            "event_id": str(uuid.uuid4()),
            "event_type": "REQUISITION_ACTION_REFUSED",
            "requisition_id": requisition_id,
            "action": action,
            "state": previous_state,
            "actor_id": actor_id,
            "actor_role": role,
            "reason": str(exc),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
        raise

    path = Path(requisitions_path)
    fieldnames, rows = _read(path)
    for row in rows:
        if row.get("requisition_id") == requisition_id:
            row.update({
                "state": requisition.state,
                "decided_by": requisition.decided_by or "",
                "decided_at": requisition.decided_at or "",
                "decision_reason": requisition.decision_reason or "",
            })
    with path.open("w", encoding="utf-8", newline="") as destination:
        writer = csv.DictWriter(destination, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    audit_event = {
        "event_id": str(uuid.uuid4()),
        "event_type": f"REQUISITION_{requisition.state}",
        "requisition_id": requisition_id,
        "previous_state": previous_state,
        "state": requisition.state,
        "actor_id": actor_id,
        "reason": reason,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    _append_audit(audit_log_path, audit_event)

    return {
        "requisition_id": requisition_id,
        "previous_state": previous_state,
        "state": requisition.state,
        "decided_by": requisition.decided_by,
        "audit_event_id": audit_event["event_id"],
    }


def _append_audit(audit_log_path: Path | str, event: dict[str, Any]) -> None:
    audit_path = Path(audit_log_path)
    audit_path.parent.mkdir(parents=True, exist_ok=True)
    with audit_path.open("a", encoding="utf-8") as audit_file:
        audit_file.write(json.dumps(event, sort_keys=True) + "\n")


__all__ = ["load_requisition", "transition_requisition"]
