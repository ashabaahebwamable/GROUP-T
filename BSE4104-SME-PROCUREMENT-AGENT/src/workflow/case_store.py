"""SQLite persistence for resumable procurement workflow cases."""

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
import sqlite3
from typing import Any, Generator

from src.workflow.state_machine import (
    Requisition,
    approve,
    halt,
    query,
    reject,
    start_draft,
    submit_for_approval,
)
from src.workflow.users import role_of


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DATABASE_PATH = PROJECT_ROOT / "data" / "application_state.sqlite3"
RESUMABLE_STATES = ("OPEN", "DRAFT", "PENDING_APPROVAL")


@dataclass(frozen=True)
class WorkflowCase:
    case_id: str
    state: str
    item: dict[str, Any]
    quotations: list[dict[str, Any]]
    comparison: dict[str, Any] | None
    flags: list[str]
    created_at: str
    updated_at: str
    decided_by: str | None = None
    decided_at: str | None = None
    decision_reason: str | None = None


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _json_dump(value: Any, field: str) -> str:
    try:
        return json.dumps(value, sort_keys=True, allow_nan=False)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field} must contain JSON-serializable values") from exc


class CaseStore:
    """Store case details and state transitions in a local SQLite database."""

    def __init__(self, database_path: Path | str = DEFAULT_DATABASE_PATH) -> None:
        self.database_path = Path(database_path)
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    @contextmanager
    def _connect(self) -> Generator[sqlite3.Connection, None, None]:
        connection = sqlite3.connect(self.database_path, timeout=10)
        connection.row_factory = sqlite3.Row
        try:
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS workflow_cases (
                    case_id TEXT PRIMARY KEY,
                    state TEXT NOT NULL CHECK (
                        state IN ('OPEN', 'DRAFT', 'PENDING_APPROVAL',
                                  'APPROVED', 'REJECTED', 'QUERIED', 'HALTED')
                    ),
                    item_json TEXT NOT NULL,
                    quotations_json TEXT NOT NULL,
                    comparison_json TEXT,
                    flags_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    decided_by TEXT,
                    decided_at TEXT,
                    decision_reason TEXT
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS workflow_case_events (
                    event_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    case_id TEXT NOT NULL REFERENCES workflow_cases(case_id),
                    previous_state TEXT,
                    state TEXT NOT NULL,
                    actor_id TEXT,
                    reason TEXT,
                    occurred_at TEXT NOT NULL
                )
                """
            )

    @staticmethod
    def _validate_case_id(case_id: str) -> None:
        if not isinstance(case_id, str) or not case_id.strip():
            raise ValueError("case_id is required")

    @staticmethod
    def _decode(row: sqlite3.Row) -> WorkflowCase:
        return WorkflowCase(
            case_id=row["case_id"],
            state=row["state"],
            item=json.loads(row["item_json"]),
            quotations=json.loads(row["quotations_json"]),
            comparison=(
                json.loads(row["comparison_json"])
                if row["comparison_json"] is not None
                else None
            ),
            flags=json.loads(row["flags_json"]),
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            decided_by=row["decided_by"],
            decided_at=row["decided_at"],
            decision_reason=row["decision_reason"],
        )

    def create_case(
        self,
        case_id: str,
        *,
        item: dict[str, Any] | None = None,
        quotations: list[dict[str, Any]] | None = None,
        comparison: dict[str, Any] | None = None,
        flags: list[str] | None = None,
    ) -> WorkflowCase:
        """Create a case in OPEN state with its currently available evidence."""
        self._validate_case_id(case_id)
        item = {} if item is None else item
        quotations = [] if quotations is None else quotations
        flags = [] if flags is None else flags
        self._validate_data(item, quotations, comparison, flags)
        now = _now_iso()
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO workflow_cases (
                    case_id, state, item_json, quotations_json, comparison_json,
                    flags_json, created_at, updated_at
                ) VALUES (?, 'OPEN', ?, ?, ?, ?, ?, ?)
                """,
                (
                    case_id,
                    _json_dump(item, "item"),
                    _json_dump(quotations, "quotations"),
                    _json_dump(comparison, "comparison"),
                    _json_dump(flags, "flags"),
                    now,
                    now,
                ),
            )
            connection.execute(
                """
                INSERT INTO workflow_case_events
                    (case_id, previous_state, state, occurred_at)
                VALUES (?, NULL, 'OPEN', ?)
                """,
                (case_id, now),
            )
        return self.get_case(case_id)

    @staticmethod
    def _validate_data(
        item: dict[str, Any],
        quotations: list[dict[str, Any]],
        comparison: dict[str, Any] | None,
        flags: list[str],
    ) -> None:
        if not isinstance(item, dict):
            raise ValueError("item must be an object")
        if not isinstance(quotations, list) or any(
            not isinstance(quotation, dict) for quotation in quotations
        ):
            raise ValueError("quotations must be a list of objects")
        if comparison is not None and not isinstance(comparison, dict):
            raise ValueError("comparison must be an object or None")
        if not isinstance(flags, list) or any(
            not isinstance(flag, str) for flag in flags
        ):
            raise ValueError("flags must be a list of strings")

    def get_case(self, case_id: str) -> WorkflowCase:
        """Restore a case and all its persisted evidence."""
        self._validate_case_id(case_id)
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM workflow_cases WHERE case_id = ?", (case_id,)
            ).fetchone()
        if row is None:
            raise ValueError(f"Unknown case: {case_id}")
        return self._decode(row)

    def list_resumable_cases(self) -> list[WorkflowCase]:
        """Return open workflow cases in their most recently updated order."""
        placeholders = ", ".join("?" for _ in RESUMABLE_STATES)
        with self._connect() as connection:
            rows = connection.execute(
                f"""
                SELECT * FROM workflow_cases
                WHERE state IN ({placeholders})
                ORDER BY updated_at DESC, case_id
                """,
                RESUMABLE_STATES,
            ).fetchall()
        return [self._decode(row) for row in rows]

    def update_case_data(
        self,
        case_id: str,
        *,
        item: dict[str, Any],
        quotations: list[dict[str, Any]],
        comparison: dict[str, Any] | None,
        flags: list[str],
    ) -> WorkflowCase:
        """Persist the latest item, quotations, computed comparison and flags."""
        self._validate_case_id(case_id)
        self._validate_data(item, quotations, comparison, flags)
        with self._connect() as connection:
            cursor = connection.execute(
                """
                UPDATE workflow_cases
                SET item_json = ?, quotations_json = ?, comparison_json = ?,
                    flags_json = ?, updated_at = ?
                WHERE case_id = ? AND state IN ('OPEN', 'DRAFT', 'PENDING_APPROVAL')
                """,
                (
                    _json_dump(item, "item"),
                    _json_dump(quotations, "quotations"),
                    _json_dump(comparison, "comparison"),
                    _json_dump(flags, "flags"),
                    _now_iso(),
                    case_id,
                ),
            )
            if cursor.rowcount == 0:
                exists = connection.execute(
                    "SELECT 1 FROM workflow_cases WHERE case_id = ?", (case_id,)
                ).fetchone()
                if exists is None:
                    raise ValueError(f"Unknown case: {case_id}")
                raise ValueError("Cannot update evidence on a terminal case")
        return self.get_case(case_id)

    def transition_case(
        self,
        case_id: str,
        action: str,
        *,
        actor_id: str | None = None,
        reason: str | None = None,
    ) -> WorkflowCase:
        """Apply one legal state transition atomically with its event record."""
        self._validate_case_id(case_id)
        now = _now_iso()
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                "SELECT * FROM workflow_cases WHERE case_id = ?", (case_id,)
            ).fetchone()
            if row is None:
                raise ValueError(f"Unknown case: {case_id}")

            # US-09 separation of duties: whoever submitted the case for
            # approval prepared it, and may not also decide it.
            submitter = connection.execute(
                """
                SELECT actor_id FROM workflow_case_events
                WHERE case_id = ? AND state = 'PENDING_APPROVAL'
                ORDER BY event_id DESC LIMIT 1
                """,
                (case_id,),
            ).fetchone()
            requisition = Requisition(
                requisition_id=case_id,
                state=row["state"],
                policy_flags=json.loads(row["flags_json"]),
                created_by=submitter["actor_id"] if submitter else None,
                decided_by=row["decided_by"],
                decided_at=row["decided_at"],
                decision_reason=row["decision_reason"],
            )
            if requisition.decided_by is not None:
                requisition.decided_by = str(requisition.decided_by).strip() or None
            if requisition.decision_reason is not None:
                requisition.decision_reason = str(requisition.decision_reason).strip() or None
            if action == "start_draft":
                start_draft(requisition)
            elif action == "submit":
                submit_for_approval(requisition)
            elif action == "approve":
                approve(requisition, approver_id=actor_id or "",
                        approver_role=role_of(actor_id))
            elif action == "reject":
                reject(requisition, approver_id=actor_id or "",
                       approver_role=role_of(actor_id), reason=reason or "")
            elif action == "query":
                query(requisition, approver_id=actor_id or "",
                      approver_role=role_of(actor_id), reason=reason or "")
            elif action == "halt":
                halt(requisition, reason=reason or "")
            else:
                raise ValueError(f"Unknown case action: {action!r}")

            previous_state = row["state"]
            decision_by = requisition.decided_by
            decided_at = requisition.decided_at
            decision_reason = requisition.decision_reason
            cursor = connection.execute(
                """
                UPDATE workflow_cases
                SET state = ?, updated_at = ?, decided_by = ?,
                    decided_at = ?, decision_reason = ?
                WHERE case_id = ? AND state = ?
                """,
                (
                    requisition.state,
                    now,
                    decision_by,
                    decided_at,
                    decision_reason,
                    case_id,
                    previous_state,
                ),
            )
            if cursor.rowcount != 1:
                raise RuntimeError(f"Concurrent state change detected for case {case_id}")
            connection.execute(
                """
                INSERT INTO workflow_case_events
                    (case_id, previous_state, state, actor_id, reason, occurred_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (case_id, previous_state, requisition.state, actor_id, reason, now),
            )

        return self.get_case(case_id)

    def get_case_events(self, case_id: str) -> list[dict[str, Any]]:
        """Return the ordered transition history for a case."""
        self._validate_case_id(case_id)
        with self._connect() as connection:
            exists = connection.execute(
                "SELECT 1 FROM workflow_cases WHERE case_id = ?", (case_id,)
            ).fetchone()
            if exists is None:
                raise ValueError(f"Unknown case: {case_id}")
            rows = connection.execute(
                """
                SELECT previous_state, state, actor_id, reason, occurred_at
                FROM workflow_case_events
                WHERE case_id = ? ORDER BY event_id
                """,
                (case_id,),
            ).fetchall()
        return [dict(row) for row in rows]


__all__ = [
    "DEFAULT_DATABASE_PATH",
    "RESUMABLE_STATES",
    "CaseStore",
    "WorkflowCase",
]
