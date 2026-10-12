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
