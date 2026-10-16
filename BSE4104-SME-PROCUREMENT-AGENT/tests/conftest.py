"""Shared test isolation.

run_agent persists every run to the tool trace and the audit log. Point both
at a temporary directory so the test suite never writes into the repository's
evidence files. A test that needs a specific path can still patch it itself.
"""

import pytest

from src.agent import tools_router
from src.tools import procurement


@pytest.fixture(autouse=True)
def _isolate_run_logs(tmp_path, monkeypatch):
    monkeypatch.setattr(tools_router, "TOOL_TRACE_PATH", tmp_path / "tool-calls.jsonl")
    monkeypatch.setattr(procurement, "AUDIT_LOG_PATH", tmp_path / "audit-log.jsonl")


@pytest.fixture(autouse=True)
def _isolate_preference_database(tmp_path, monkeypatch):
    """Keep confirm_supplier() and the router off the real preferences database.

    The memory functions bind their default database path when they are
    defined, so patching a path constant has no effect. Wrap the names the
    loop and the router actually call instead. A test that patches these names
    itself still takes precedence.
    """
    from functools import partial

    from src.agent import loop
    from src.memory import supplier_preferences

    database = tmp_path / "application_state.sqlite3"
    monkeypatch.setattr(
        loop,
        "record_supplier_preference",
        partial(supplier_preferences.record_supplier_preference, database_path=database),
    )
    monkeypatch.setattr(
        tools_router,
        "get_supplier_preference_hint",
        partial(supplier_preferences.get_supplier_preference_hint, database_path=database),
    )
