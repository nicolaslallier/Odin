import os
from unittest.mock import patch
from src.worker.tasks import maintenance

# --------- Cleanup Old Logs Task (all branches) ---------


def base_env(monkeypatch, postgres_dsn=None, celery_backend=None):
    # Set up the env for config fallback logic
    monkeypatch.setitem(os.environ, "CELERY_BROKER_URL", "memory://")
    if postgres_dsn:
        monkeypatch.setitem(os.environ, "POSTGRES_DSN", postgres_dsn)
    else:
        os.environ.pop("POSTGRES_DSN", None)
    if celery_backend:
        monkeypatch.setitem(os.environ, "CELERY_RESULT_BACKEND", celery_backend)
    else:
        os.environ.pop("CELERY_RESULT_BACKEND", None)


@patch("asyncio.run")
def test_cleanup_old_logs_happy_dispose(mock_run, monkeypatch):
    base_env(monkeypatch, postgres_dsn="postgresql+asyncpg://foo/bar")
    mock_run.return_value = 123
    result = maintenance.cleanup_old_logs_task.run()
    assert result["deleted_count"] == 123
    assert result["status"] == "success"
    mock_run.assert_called_once()


@patch("asyncio.run")
def test_cleanup_old_logs_dsn_fallback(mock_run, monkeypatch):
    # DSN only from result backend triggers fallback logic (line 59)
    base_env(monkeypatch, postgres_dsn=None, celery_backend="db+postgresql://user:pass@host/db")
    mock_run.return_value = 99
    result = maintenance.cleanup_old_logs_task.run()
    assert result["deleted_count"] == 99
    assert result["status"] == "success"


@patch("asyncio.run")
def test_cleanup_old_logs_no_db(mock_run, monkeypatch):
    base_env(monkeypatch, postgres_dsn=None, celery_backend=None)
    result = maintenance.cleanup_old_logs_task.run()
    assert result["status"] == "error"
    assert "No database" in result["message"] or "connection" in result["message"]
    assert result["deleted_count"] == 0
    mock_run.assert_not_called()


@patch("asyncio.run")
def test_cleanup_old_logs_async_error(mock_run, monkeypatch):
    base_env(monkeypatch, postgres_dsn="postgresql+asyncpg://err/db")
    mock_run.side_effect = Exception("fail-cleanup")
    result = maintenance.cleanup_old_logs_task.run()
    assert result["status"] == "error"
    assert "fail-cleanup" in result["message"]
    assert result["deleted_count"] == 0


@patch("asyncio.run")
def test_cleanup_old_logs_env_override(mock_run, monkeypatch):
    base_env(monkeypatch, postgres_dsn="postgresql+asyncpg://foo/bar")
    monkeypatch.setitem(os.environ, "LOG_RETENTION_DAYS", "77")
    mock_run.return_value = 55
    result = maintenance.cleanup_old_logs_task.run()
    assert result["retention_days"] == 77
    assert result["deleted_count"] == 55


# --------- Log Statistics Task (all branches) ---------


@patch("asyncio.run")
def test_log_statistics_happy(mock_run, monkeypatch):
    base_env(monkeypatch, postgres_dsn="postgresql+asyncpg://foo/bar")
    # simulate all expected stats fields and non-none times
    fake_stats = {
        "status": "success",
        "total_logs": 50,
        "table_size": "123 MB",
        "by_level": {"INFO": 45, "ERROR": 5},
        "oldest_log": "2023-01-01T00:00:00",
        "newest_log": "2024-01-01T00:00:00",
        "timestamp": "2024-02-21T14:00:00",
    }
    mock_run.return_value = fake_stats
    result = maintenance.log_statistics_task.run()
    assert result["status"] == "success"
    assert result["total_logs"] == 50
    assert "INFO" in result["by_level"]
    assert result["table_size"] == "123 MB"
    assert result["oldest_log"] and result["newest_log"]


@patch("asyncio.run")
def test_log_statistics_db_missing(mock_run, monkeypatch):
    base_env(monkeypatch, postgres_dsn=None, celery_backend=None)
    result = maintenance.log_statistics_task.run()
    assert result["status"] == "error"
    assert "No database" in result["message"] or "connection" in result["message"]
    mock_run.assert_not_called()


@patch("asyncio.run")
def test_log_statistics_dsn_fallback(mock_run, monkeypatch):
    base_env(monkeypatch, postgres_dsn=None, celery_backend="db+postgresql://u:pw@h/db")
    fake_stats = {
        "status": "success",
        "total_logs": 5,
        "table_size": "10 MB",
        "by_level": {},
        "oldest_log": None,
        "newest_log": None,
        "timestamp": "2024",
    }
    mock_run.return_value = fake_stats
    result = maintenance.log_statistics_task.run()
    assert result["status"] == "success"
    assert result["total_logs"] == 5
    assert result["oldest_log"] is None


@patch("asyncio.run")
def test_log_statistics_async_error(mock_run, monkeypatch):
    base_env(monkeypatch, postgres_dsn="postgresql+asyncpg://foo/bar")
    mock_run.side_effect = Exception("fail-stats")
    result = maintenance.log_statistics_task.run()
    assert result["status"] == "error"
    assert "fail-stats" in result["message"] or "fail-stats" in result["message"]


@patch("asyncio.run")
def test_log_statistics_none_times(mock_run, monkeypatch):
    base_env(monkeypatch, postgres_dsn="postgresql+asyncpg://foo/bar")
    fake_stats = {
        "status": "success",
        "total_logs": 2,
        "table_size": "15 MB",
        "by_level": {},
        "oldest_log": None,
        "newest_log": None,
        "timestamp": "2024-05-20T00:00:00",
    }
    mock_run.return_value = fake_stats
    result = maintenance.log_statistics_task.run()
    assert result["oldest_log"] is None
    assert result["newest_log"] is None
