import pytest
from fastapi import HTTPException
from src.api.routes import logs
from src.api.exceptions import ValidationError, DatabaseError
import types

@pytest.mark.asyncio
async def test_get_log_service_error():
    req = types.SimpleNamespace(app=types.SimpleNamespace(state=types.SimpleNamespace(container=None)))
    with pytest.raises(HTTPException) as ex:
        await logs.get_log_service(req)
    assert ex.value.status_code == 500
    assert "Failed to initialize log service" in ex.value.detail

@pytest.mark.asyncio
async def test_get_llm_analyzer_error():
    req = types.SimpleNamespace(app=types.SimpleNamespace(state=types.SimpleNamespace(container=None)))
    with pytest.raises(HTTPException) as ex:
        await logs.get_llm_analyzer(req)
    assert ex.value.status_code == 500
    assert "Failed to initialize LLM analyzer" in ex.value.detail

@pytest.mark.asyncio
async def test_get_logs_validation_error(monkeypatch):
    async def mock_get_logs(*a, **k):
        raise ValidationError("vfail")
    req = types.SimpleNamespace(app=types.SimpleNamespace(state=types.SimpleNamespace(container=types.SimpleNamespace(database=types.SimpleNamespace(get_session=lambda: dummy_ctx_manager())))))
    monkeypatch.setattr("src.api.repositories.log_repository.LogRepository.get_logs", mock_get_logs)
    with pytest.raises(HTTPException) as ex:
        await logs.get_logs(request=req)
    assert ex.value.status_code == 400
    assert "vfail" in ex.value.detail

@pytest.mark.asyncio
async def test_get_logs_database_error(monkeypatch):
    async def mock_get_logs(*a, **k):
        raise DatabaseError("dberr")
    req = types.SimpleNamespace(app=types.SimpleNamespace(state=types.SimpleNamespace(container=types.SimpleNamespace(database=types.SimpleNamespace(get_session=lambda: dummy_ctx_manager())))))
    monkeypatch.setattr("src.api.repositories.log_repository.LogRepository.get_logs", mock_get_logs)
    with pytest.raises(HTTPException) as ex:
        await logs.get_logs(request=req)
    assert ex.value.status_code == 500
    assert "dberr" in ex.value.detail

@pytest.mark.asyncio
async def test_get_logs_unexpected_error(monkeypatch):
    async def mock_get_logs(*a, **k): raise Exception("boom")
    req = types.SimpleNamespace(app=types.SimpleNamespace(state=types.SimpleNamespace(container=types.SimpleNamespace(database=types.SimpleNamespace(get_session=lambda: dummy_ctx_manager())))))
    monkeypatch.setattr("src.api.repositories.log_repository.LogRepository.get_logs", mock_get_logs)
    with pytest.raises(HTTPException) as ex:
        await logs.get_logs(request=req)
    assert ex.value.status_code == 500
    assert "Unexpected error" in ex.value.detail

# Helper for dummy async context manager
def dummy_ctx_manager():
    class Dummy:
        async def __aenter__(self): return Dummy()
        async def __aexit__(self, exc_type, exc, tb): return None
    return Dummy()
