"""Durable supplier preferences that are only written after human confirmation."""

from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
import sqlite3
from typing import Generator

from src.workflow.case_store import DEFAULT_DATABASE_PATH


class PreferenceConfirmationRequiredError(ValueError):
    """Raised when a preference write is attempted without explicit consent."""


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
) -> dict[str, str]:
    """Persist a preference only when an identified human explicitly confirms."""
    if confirmed is not True:
        raise PreferenceConfirmationRequiredError(
            "A supplier preference requires explicit human confirmation."
        )
    item_id = _required_text(item_id, "item_id")
    supplier_id = _required_text(supplier_id, "supplier_id")
    confirmer_id = _required_text(confirmer_id, "confirmer_id")
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


def get_supplier_preference_hint(
    item_id: str,
    *,
    database_path: Path | str = DEFAULT_DATABASE_PATH,
) -> dict[str, str] | None:
    """Return the latest confirmed preference as a hint, never as a ranking input."""
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
    if row is None:
        return None
    return {
        "item_id": item_id,
        "supplier_id": row[0],
        "confirmed_by": row[1],
        "confirmed_at": row[2],
        "message": "Previously confirmed preference; informational only and not used in ranking.",
    }


__all__ = [
    "PreferenceConfirmationRequiredError",
    "record_supplier_preference",
    "get_supplier_preference_hint",
]
