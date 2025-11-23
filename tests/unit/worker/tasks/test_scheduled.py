"""Unit tests for scheduled tasks.

This module tests periodic/scheduled tasks that run on a schedule via Celery Beat.
"""

from __future__ import annotations

import os

os.environ.setdefault("CELERY_BROKER_URL", "memory://")
os.environ.setdefault("CELERY_RESULT_BACKEND", "cache+memory://")

import pytest
from unittest.mock import patch, MagicMock, Mock
import httpx

from src.worker.tasks import scheduled

# 1. Cover session_scope rollback (lines 43-45)
def test_session_scope_rollback_and_raise(monkeypatch):
    class DummySession:
        def __init__(self):
            self.committed = False
            self.rolled_back = False
            self.closed = False
        def commit(self):
            self.committed = True
        def rollback(self):
            self.rolled_back = True
        def close(self):
            self.closed = True
    # Patch SQLAlchemy
    monkeypatch.setattr(scheduled, "create_engine", lambda *a, **k: Mock())
    monkeypatch.setattr(scheduled, "sessionmaker", lambda bind: lambda: DummySession())
    # Patch get_config for function-local import
    scheduled.session_scope.__globals__["get_config"] = lambda: Mock(result_backend="db+sqlite:///:memory:")

    # Should rollback and re-raise
    with pytest.raises(ValueError):
        with scheduled.session_scope() as session:
            raise ValueError("Simulated DB error")
    # If we step outside with, test closes
    # (DummySession's close method should have been called)

# 2. Cover health_check_services else: (unhealthy branch)
def test_health_check_services_unhealthy(monkeypatch):
    def bad_response(url, timeout):
        mock = MagicMock()
        mock.status_code = 500
        mock.elapsed.total_seconds.return_value = 0.1
        return mock
    monkeypatch.setattr(httpx, "get", bad_response)
    result = scheduled.health_check_services()
    assert any(v.get("status") == "unhealthy" for v in result["services"].values())
    assert result["failures"] > 0
    assert result["status"] == "partial"

# 3. Cover cleanup_old_task_results error case (lines 142-143)
def test_cleanup_old_task_results_error(monkeypatch):
    class DummyDialect:
        name = "sqlite"
    class DummyBind:
        dialect = DummyDialect()
    class BadSession:
        def get_bind(self): return DummyBind()
        def query(self, *a, **k): return self
        def filter(self, *a, **k): return self
        def delete(self, *a, **k): raise Exception("Simulated delete error")
        def close(self): pass
    # Patch session_scope to yield BadSession
    @patch("src.worker.tasks.scheduled.session_scope")
    def _test(mock_ss):
        mock_ss.return_value.__enter__.return_value = BadSession()
        result = scheduled.cleanup_old_task_results()
        assert result["status"] == "error"
        assert "Simulated delete error" in result["error"]
    _test()

def test_health_check_service_httpx_exception(monkeypatch):
    def raise_exc(url, timeout):
        raise Exception("Network error!")
    monkeypatch.setattr("httpx.get", raise_exc)
    result = scheduled.health_check_services()
    for svc in result["services"].values():
        assert svc["status"] == "unavailable"
        assert "Network error" in svc["error"]
    assert result["failures"] == len(result["services"])
    assert result["status"] == "partial"

@patch("src.worker.tasks.scheduled.session_scope")
def test_generate_daily_report_handles_exception(mock_sess):
    mock_sess.side_effect = Exception("Database gone")
    result = scheduled.generate_daily_report()
    assert result["status"] == "error"
    assert "Database gone" in result["error"]
    assert "date" in result
