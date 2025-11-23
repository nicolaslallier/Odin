import pytest
from fastapi import HTTPException
from src.api.routes import logs
from src.api.exceptions import ValidationError, DatabaseError
import types


@pytest.mark.asyncio
async def test_get_log_service_error():
    req = types.SimpleNamespace(
        app=types.SimpleNamespace(state=types.SimpleNamespace(container=None))
    )
    with pytest.raises(HTTPException) as ex:
        await logs.get_log_service(req)
    assert ex.value.status_code == 500
    assert "Failed to initialize log service" in ex.value.detail


@pytest.mark.asyncio
async def test_get_llm_analyzer_error():
    req = types.SimpleNamespace(
        app=types.SimpleNamespace(state=types.SimpleNamespace(container=None))
    )
    with pytest.raises(HTTPException) as ex:
        await logs.get_llm_analyzer(req)
    assert ex.value.status_code == 500
    assert "Failed to initialize LLM analyzer" in ex.value.detail


@pytest.mark.asyncio
async def test_get_logs_validation_error(monkeypatch):
    async def mock_get_logs(*a, **k):
        raise ValidationError("vfail")

    monkeypatch.setattr("src.api.services.log_service.LogService.get_logs", mock_get_logs)
    req = dummy_req()
    with pytest.raises(HTTPException) as ex:
        await logs.get_logs(request=req)
    assert ex.value.status_code == 400
    assert "vfail" in ex.value.detail


@pytest.mark.asyncio
async def test_get_logs_database_error(monkeypatch):
    async def mock_get_logs(*a, **k):
        raise DatabaseError("dberr")

    monkeypatch.setattr("src.api.services.log_service.LogService.get_logs", mock_get_logs)
    req = dummy_req()
    with pytest.raises(HTTPException) as ex:
        await logs.get_logs(request=req)
    assert ex.value.status_code == 500
    assert "dberr" in ex.value.detail


@pytest.mark.asyncio
async def test_get_logs_unexpected_error(monkeypatch):
    async def mock_get_logs(*a, **k):
        raise Exception("boom")

    monkeypatch.setattr("src.api.services.log_service.LogService.get_logs", mock_get_logs)
    req = dummy_req()
    with pytest.raises(HTTPException) as ex:
        await logs.get_logs(request=req)
    assert ex.value.status_code == 500
    assert "Unexpected error" in ex.value.detail


# Additional error-path endpoint coverage:
@pytest.mark.asyncio
async def test_search_logs_validation_error(monkeypatch):
    async def err(*a, **k):
        raise ValidationError("slog")

    monkeypatch.setattr("src.api.services.log_service.LogService.search_logs", err)
    req = dummy_req()
    with pytest.raises(HTTPException) as ex:
        await logs.search_logs(q="a", request=req)
    assert ex.value.status_code == 400
    assert "slog" in ex.value.detail


@pytest.mark.asyncio
async def test_search_logs_database_error(monkeypatch):
    async def err(*a, **k):
        raise DatabaseError("slog-db")

    monkeypatch.setattr("src.api.services.log_service.LogService.search_logs", err)
    req = dummy_req()
    with pytest.raises(HTTPException) as ex:
        await logs.search_logs(q="a", request=req)
    assert ex.value.status_code == 500


@pytest.mark.asyncio
async def test_search_logs_unexpected_error(monkeypatch):
    async def err(*a, **k):
        raise Exception("slog-unknown")

    monkeypatch.setattr("src.api.services.log_service.LogService.search_logs", err)
    req = dummy_req()
    with pytest.raises(HTTPException) as ex:
        await logs.search_logs(q="a", request=req)
    assert ex.value.status_code == 500
    assert "Unexpected error" in ex.value.detail


@pytest.mark.asyncio
async def test_get_log_statistics_validation_error(monkeypatch):
    async def err(*a, **k):
        raise ValidationError("statfail")

    monkeypatch.setattr("src.api.services.log_service.LogService.get_statistics", err)
    req = dummy_req()
    with pytest.raises(HTTPException) as ex:
        await logs.get_log_statistics(request=req)
    assert ex.value.status_code == 400


@pytest.mark.asyncio
async def test_get_log_statistics_database_error(monkeypatch):
    async def err(*a, **k):
        raise DatabaseError("stat-db")

    monkeypatch.setattr("src.api.services.log_service.LogService.get_statistics", err)
    req = dummy_req()
    with pytest.raises(HTTPException) as ex:
        await logs.get_log_statistics(request=req)
    assert ex.value.status_code == 500


@pytest.mark.asyncio
async def test_get_log_statistics_unexpected_error(monkeypatch):
    async def err(*a, **k):
        raise Exception("stat-unknown")

    monkeypatch.setattr("src.api.services.log_service.LogService.get_statistics", err)
    req = dummy_req()
    with pytest.raises(HTTPException) as ex:
        await logs.get_log_statistics(request=req)
    assert ex.value.status_code == 500
    assert "Unexpected error" in ex.value.detail


@pytest.mark.asyncio
async def test_get_correlated_logs_validation_error(monkeypatch):
    async def err(*a, **k):
        raise ValidationError("corrfail")

    monkeypatch.setattr("src.api.services.log_service.LogService.get_related_logs", err)
    req = dummy_req()
    with pytest.raises(HTTPException) as ex:
        await logs.get_correlated_logs(request=req)
    assert ex.value.status_code == 400


@pytest.mark.asyncio
async def test_get_correlated_logs_database_error(monkeypatch):
    async def err(*a, **k):
        raise DatabaseError("corr-db")

    monkeypatch.setattr("src.api.services.log_service.LogService.get_related_logs", err)
    req = dummy_req()
    with pytest.raises(HTTPException) as ex:
        await logs.get_correlated_logs(request=req)
    assert ex.value.status_code == 500


@pytest.mark.asyncio
async def test_get_correlated_logs_unexpected_error(monkeypatch):
    async def err(*a, **k):
        raise Exception("corr-unknown")

    monkeypatch.setattr("src.api.services.log_service.LogService.get_related_logs", err)
    req = dummy_req()
    with pytest.raises(HTTPException) as ex:
        await logs.get_correlated_logs(request=req)
    assert ex.value.status_code == 500
    assert "Unexpected error" in ex.value.detail


@pytest.mark.asyncio
async def test_analyze_logs_validation_error(monkeypatch):
    async def err(*a, **k):
        raise ValidationError("afail")

    monkeypatch.setattr("src.api.services.log_service.LogService.get_logs", err)
    req = dummy_req()
    analysis_request = types.SimpleNamespace(
        log_ids=None, search_criteria=None, analysis_type="root_cause", max_logs=10
    )
    with pytest.raises(HTTPException) as ex:
        await logs.analyze_logs(analysis_request, request=req)
    assert ex.value.status_code == 400


@pytest.mark.asyncio
async def test_analyze_logs_database_error(monkeypatch):
    async def err(*a, **k):
        raise DatabaseError("adb")

    monkeypatch.setattr("src.api.services.log_service.LogService.get_logs", err)
    req = dummy_req()
    analysis_request = types.SimpleNamespace(
        log_ids=None, search_criteria=None, analysis_type="root_cause", max_logs=10
    )
    with pytest.raises(HTTPException) as ex:
        await logs.analyze_logs(analysis_request, request=req)
    assert ex.value.status_code == 500


@pytest.mark.asyncio
async def test_analyze_logs_unexpected_error(monkeypatch):
    async def err(*a, **k):
        return []  # simulate no logs found triggers ValidationError

    monkeypatch.setattr("src.api.services.log_service.LogService.get_logs", err)
    req = dummy_req()
    analysis_request = types.SimpleNamespace(
        log_ids=None, search_criteria=None, analysis_type="root_cause", max_logs=10
    )
    with pytest.raises(HTTPException) as ex:
        await logs.analyze_logs(analysis_request, request=req)
    assert ex.value.status_code == 400
    assert "No logs found" in ex.value.detail


@pytest.mark.asyncio
async def test_get_log_by_id_validation_error(monkeypatch):
    async def err(*a, **k):
        raise ValidationError("lidfail")

    monkeypatch.setattr("src.api.services.log_service.LogService.get_log_by_id", err)
    req = dummy_req()
    with pytest.raises(HTTPException) as ex:
        await logs.get_log_by_id(log_id=123, request=req)
    assert ex.value.status_code == 400


@pytest.mark.asyncio
async def test_get_log_by_id_database_error(monkeypatch):
    async def err(*a, **k):
        raise DatabaseError("lid-db")

    monkeypatch.setattr("src.api.services.log_service.LogService.get_log_by_id", err)
    req = dummy_req()
    with pytest.raises(HTTPException) as ex:
        await logs.get_log_by_id(log_id=123, request=req)
    assert ex.value.status_code == 500


@pytest.mark.asyncio
async def test_get_log_by_id_http_exception(monkeypatch):
    from fastapi import HTTPException as FastAPIHTTPException

    async def err(*a, **k):
        raise FastAPIHTTPException(status_code=418, detail="I'm a teapot")

    monkeypatch.setattr("src.api.services.log_service.LogService.get_log_by_id", err)
    req = dummy_req()
    with pytest.raises(FastAPIHTTPException) as ex:
        await logs.get_log_by_id(log_id=123, request=req)
    assert ex.value.status_code == 418


@pytest.mark.asyncio
async def test_get_log_by_id_unexpected_error(monkeypatch):
    async def err(*a, **k):
        raise Exception("lx")

    monkeypatch.setattr("src.api.services.log_service.LogService.get_log_by_id", err)
    req = dummy_req()
    with pytest.raises(HTTPException) as ex:
        await logs.get_log_by_id(log_id=123, request=req)
    assert ex.value.status_code == 500


def dummy_req():
    class DummySession:
        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc_val, exc_tb):
            return None

    database = types.SimpleNamespace(get_session=lambda: DummySession())
    container = types.SimpleNamespace(database=database)
    state = types.SimpleNamespace(container=container)
    app = types.SimpleNamespace(state=state)
    return types.SimpleNamespace(app=app)
