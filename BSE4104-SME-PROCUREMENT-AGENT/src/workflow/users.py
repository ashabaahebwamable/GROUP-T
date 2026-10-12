"""User-role registry for authorisation (US-09).

Roles come from ``data/users.csv``, never from the caller, so a person cannot
approve by claiming to be an approver. Unknown users have no role.
"""

from __future__ import annotations

import csv
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
USERS_PATH = PROJECT_ROOT / "data" / "users.csv"
APPROVER_ROLE = "approver"


def role_of(user_id: str | None, *, users_path: Path | str | None = None) -> str | None:
    """Return the registered role of ``user_id``, or None if it is not registered."""
    if not user_id or not str(user_id).strip():
        return None
    path = Path(users_path) if users_path is not None else USERS_PATH
    if not path.is_file():
        return None
    with path.open("r", encoding="utf-8-sig", newline="") as source:
        for row in csv.DictReader(source):
            if row.get("user_id") == str(user_id).strip():
                return (row.get("role") or "").strip().lower() or None
    return None


__all__ = ["APPROVER_ROLE", "USERS_PATH", "role_of"]
