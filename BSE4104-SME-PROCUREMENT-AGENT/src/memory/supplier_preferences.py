"""Durable supplier preferences that are only written after human confirmation.

Data handling (docs/architecture/memory-design-note.md):
- a preference is kept for RETENTION_DAYS after its confirmation; older rows are
  never shown and are removed by ``purge_expired_preferences``;
- only an approver may delete preferences, and every deletion (or refused
  attempt) is written to the audit log;
- people may list preferences only with the officer or approver role.
"""

from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import sqlite3
from typing import Any, Generator
import uuid

from src.tools import procurement
from src.workflow.case_store import DEFAULT_DATABASE_PATH
from src.workflow.users import APPROVER_ROLE, role_of


RETENTION_DAYS = 365
READER_ROLES = {"officer", APPROVER_ROLE}


class PreferenceConfirmationRequiredError(ValueError):
    """Raised when a preference write is attempted without explicit consent."""


class PreferenceAccessDeniedError(PermissionError):
    """Raised when someone without the required role reads or deletes preferences."""


@contextmanager
def _connect(database_path: Path) -> Generator[sqlite3.Connection, None, None]:
    connection = sqlite3.connect(database_path, timeout=10)
    try:
        yield connection
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def _required_text(value: str, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} is required")
    return value.strip()


def _initialize(database_path: Path) -> None:
    database_path.parent.mkdir(parents=True, exist_ok=True)
    with _connect(database_path) as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS supplier_preferences (
                preference_id INTEGER PRIMARY KEY AUTOINCREMENT,
                item_id TEXT NOT NULL,
                supplier_id TEXT NOT NULL,
                confirmed_by TEXT NOT NULL,
                confirmed_at TEXT NOT NULL
            )
            """
        )
        connection.execute(
            """
            CREATE INDEX IF NOT EXISTS supplier_preferences_by_item
            ON supplier_preferences (item_id, preference_id DESC)
            """
        )


def record_supplier_preference(
    item_id: str,
    supplier_id: str,
    *,
    confirmed: bool,
    confirmer_id: str,
    database_path: Path | str = DEFAULT_DATABASE_PATH,
    users_path: Path | str | None = None,
) -> dict[str, str]:
    """Persist a preference only when an identified human explicitly confirms.

    The confirmer must be a registered officer or approver (W6-03 security
    review), so an unknown or made-up ID cannot be recorded as the confirmer.
    """
    if confirmed is not True:
        raise PreferenceConfirmationRequiredError(
            "A supplier preference requires explicit human confirmation."
        )
    item_id = _required_text(item_id, "item_id")
    supplier_id = _required_text(supplier_id, "supplier_id")
    confirmer_id = _required_text(confirmer_id, "confirmer_id")
    if role_of(confirmer_id, users_path=users_path) not in READER_ROLES:
        raise PreferenceAccessDeniedError(
            f"{confirmer_id!r} may not confirm supplier preferences; officer or approver role required."
        )
    timestamp = datetime.now(timezone.utc).isoformat()
    path = Path(database_path)
    _initialize(path)
    with _connect(path) as connection:
        connection.execute(
            """
            INSERT INTO supplier_preferences
                (item_id, supplier_id, confirmed_by, confirmed_at)
            VALUES (?, ?, ?, ?)
            """,
            (item_id, supplier_id, confirmer_id, timestamp),
        )
    return {
        "item_id": item_id,
        "supplier_id": supplier_id,
        "confirmed_by": confirmer_id,
        "confirmed_at": timestamp,
    }


def _now(now: datetime | None) -> datetime:
    return now if now is not None else datetime.now(timezone.utc)


def _expired(confirmed_at: str, now: datetime) -> bool:
    return datetime.fromisoformat(confirmed_at) < now - timedelta(days=RETENTION_DAYS)


def _audit(event: dict[str, Any], audit_log_path: Path | str | None) -> None:
    path = Path(audit_log_path) if audit_log_path is not None else procurement.AUDIT_LOG_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    record = {
        "event_id": str(uuid.uuid4()),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        **event,
    }
    with path.open("a", encoding="utf-8") as audit_file:
        audit_file.write(json.dumps(record, sort_keys=True) + "\n")


def _table_exists(connection: sqlite3.Connection) -> bool:
    return connection.execute(
        """
        SELECT 1 FROM sqlite_master
        WHERE type = 'table' AND name = 'supplier_preferences'
        """
    ).fetchone() is not None


def get_supplier_preference_hint(
    item_id: str,
    *,
    database_path: Path | str = DEFAULT_DATABASE_PATH,
    now: datetime | None = None,
) -> dict[str, str] | None:
    """Return the latest confirmed preference as a hint, never as a ranking input.

    A preference older than RETENTION_DAYS is treated as gone.
    """
    item_id = _required_text(item_id, "item_id")
    path = Path(database_path)
    if not path.is_file():
        return None
    with _connect(path) as connection:
        table = connection.execute(
            """
            SELECT 1 FROM sqlite_master
            WHERE type = 'table' AND name = 'supplier_preferences'
            """
        ).fetchone()
        if table is None:
            return None
        row = connection.execute(
            """
            SELECT supplier_id, confirmed_by, confirmed_at
            FROM supplier_preferences
            WHERE item_id = ?
            ORDER BY preference_id DESC
            LIMIT 1
            """,
            (item_id,),
        ).fetchone()
    if row is None or _expired(row[2], _now(now)):
        return None
    return {
        "item_id": item_id,
        "supplier_id": row[0],
        "confirmed_by": row[1],
        "confirmed_at": row[2],
        "message": "Previously confirmed preference; informational only and not used in ranking.",
    }


def list_supplier_preferences(
    *,
    reader_id: str,
    database_path: Path | str = DEFAULT_DATABASE_PATH,
    users_path: Path | str | None = None,
    now: datetime | None = None,
) -> list[dict[str, str]]:
    """List current (unexpired) preferences for an officer or approver."""
    if role_of(reader_id, users_path=users_path) not in READER_ROLES:
        raise PreferenceAccessDeniedError(
            f"{reader_id!r} may not read supplier preferences; officer or approver role required."
        )
    path = Path(database_path)
    if not path.is_file():
        return []
    with _connect(path) as connection:
        if not _table_exists(connection):
            return []
        rows = connection.execute(
            """
            SELECT item_id, supplier_id, confirmed_by, confirmed_at
            FROM supplier_preferences ORDER BY item_id, preference_id DESC
            """
        ).fetchall()
    current = _now(now)
    return [
        {"item_id": r[0], "supplier_id": r[1], "confirmed_by": r[2], "confirmed_at": r[3]}
        for r in rows
        if not _expired(r[3], current)
    ]


def delete_supplier_preferences(
    item_id: str,
    *,
    deleted_by: str,
    reason: str,
    database_path: Path | str = DEFAULT_DATABASE_PATH,
    users_path: Path | str | None = None,
    audit_log_path: Path | str | None = None,
) -> int:
    """Delete every stored preference for an item. Approver only; always audited.

    Returns the number of rows deleted. A refused attempt is logged too.
    """
    item_id = _required_text(item_id, "item_id")
    reason = _required_text(reason, "reason")
    role = role_of(deleted_by, users_path=users_path)
    if role != APPROVER_ROLE:
        _audit(
            {
                "event_type": "PREFERENCE_DELETE_REFUSED",
                "item_id": item_id,
                "actor_id": deleted_by,
                "actor_role": role,
                "reason": reason,
            },
            audit_log_path,
        )
        raise PreferenceAccessDeniedError(
            f"{deleted_by!r} may not delete supplier preferences; approver role required."
        )

    path = Path(database_path)
    deleted = 0
    if path.is_file():
        with _connect(path) as connection:
            if _table_exists(connection):
                deleted = connection.execute(
                    "DELETE FROM supplier_preferences WHERE item_id = ?", (item_id,)
                ).rowcount
    _audit(
        {
            "event_type": "PREFERENCE_DELETED",
            "item_id": item_id,
            "actor_id": deleted_by,
            "actor_role": role,
            "reason": reason,
            "rows_deleted": deleted,
        },
        audit_log_path,
    )
    return deleted


def purge_expired_preferences(
    *,
    database_path: Path | str = DEFAULT_DATABASE_PATH,
    audit_log_path: Path | str | None = None,
    now: datetime | None = None,
) -> int:
    """Delete preferences older than RETENTION_DAYS; logged as a system action.

    Intended to run on a schedule (or at application start). Returns the count.
    """
    path = Path(database_path)
    if not path.is_file():
        return 0
    current = _now(now)
    with _connect(path) as connection:
        if not _table_exists(connection):
            return 0
        rows = connection.execute(
            "SELECT preference_id, confirmed_at FROM supplier_preferences"
        ).fetchall()
        expired = [r[0] for r in rows if _expired(r[1], current)]
        connection.executemany(
            "DELETE FROM supplier_preferences WHERE preference_id = ?",
            [(pid,) for pid in expired],
        )
    if expired:
        _audit(
            {
                "event_type": "PREFERENCES_PURGED",
                "actor_id": "system",
                "reason": f"older than {RETENTION_DAYS} days",
                "rows_deleted": len(expired),
            },
            audit_log_path,
        )
    return len(expired)


def model_safe_hint(hint: dict[str, Any] | None) -> dict[str, Any] | None:
    """The hint as it may be sent to an external model: supplier and message only.

    The confirming officer's ID and the time are kept on the machine
    (memory design note, data sent to the model).
    """
    if not hint:
        return hint
    return {
        "item_id": hint.get("item_id"),
        "supplier_id": hint.get("supplier_id"),
        "message": hint.get("message"),
    }


__all__ = [
    "PreferenceAccessDeniedError",
    "PreferenceConfirmationRequiredError",
    "RETENTION_DAYS",
    "delete_supplier_preferences",
    "get_supplier_preference_hint",
    "list_supplier_preferences",
    "model_safe_hint",
    "purge_expired_preferences",
    "record_supplier_preference",
]
