import pytest
from httpx import AsyncClient, ASGITransport
from unittest.mock import AsyncMock, patch, MagicMock
from fastapi import status
from src.api.app import create_app
from src.api.routes import logs as logs_route

@pytest.fixture
def log_service_mock():
    svc = MagicMock()
    svc.get_logs = AsyncMock(return_value=([{"id": 1}], 1))
    svc.search_logs = AsyncMock(return_value=([{"id": 2}], 1))
    svc.get_statistics = AsyncMock(return_value={"count": 5})
    svc.get_related_logs = AsyncMock(return_value=[{"id": 3}])
    svc.get_log_by_id = AsyncMock(return_value={"id": 4})
    svc.cleanup_old_logs = AsyncMock(return_value=2)
    svc.get_root_cause_analysis_prompt = MagicMock(return_value="prompt root cause")
    svc.get_pattern_detection_prompt = MagicMock(return_value="prompt pattern detect")
    svc.get_anomaly_detection_prompt = MagicMock(return_value="prompt anomaly detect")
    svc.get_event_correlation_prompt = MagicMock(return_value="prompt event correlation")
    svc.get_error_summarization_prompt = MagicMock(return_value="prompt error summary")
    return svc

@pytest.fixture
def app_with_overrides(log_service_mock):
    app = create_app()
    app.dependency_overrides[logs_route.get_log_service] = lambda: log_service_mock
    return app

@pytest.mark.asyncio
async def test_get_logs_happy(app_with_overrides):
    transport = ASGITransport(app=app_with_overrides)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.get("/api/v1/logs?level=INFO&limit=10&offset=0")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list) or isinstance(resp.json(), dict)

@pytest.mark.asyncio
async def test_get_logs_invalid_params(app_with_overrides):
    transport = ASGITransport(app=app_with_overrides)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        for q in ["/api/v1/logs?limit=0", "/api/v1/logs?limit=2000", "/api/v1/logs?offset=-5", "/api/v1/logs?level=ZZZ"]:
            resp = await ac.get(q)
            assert resp.status_code in (422, 400)  # Depends how ValidationError handled

@pytest.mark.asyncio
async def test_get_statistics_happy(app_with_overrides):
    transport = ASGITransport(app=app_with_overrides)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.get("/api/v1/logs/statistics")
        assert resp.status_code == 200
        assert "count" in resp.json() or resp.json() == {}

@pytest.mark.asyncio
async def test_get_statistics_invalid(app_with_overrides):
    transport = ASGITransport(app=app_with_overrides)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # Bad start_time param:
        resp = await ac.get("/api/v1/logs/statistics?start_time=not-a-date")
        assert resp.status_code in (422, 400)

@pytest.mark.asyncio
async def test_search_logs_happy(app_with_overrides):
    transport = ASGITransport(app=app_with_overrides)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.get("/api/v1/logs/search?search_term=foo")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list) or isinstance(resp.json(), dict)

@pytest.mark.asyncio
async def test_search_logs_empty(app_with_overrides):
    transport = ASGITransport(app=app_with_overrides)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.get("/api/v1/logs/search?search_term=")
        assert resp.status_code in (422, 400)

@pytest.mark.asyncio
async def test_get_log_by_id_happy(app_with_overrides):
    transport = ASGITransport(app=app_with_overrides)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.get("/api/v1/logs/4")
        assert resp.status_code == 200
        assert resp.json().get("id") == 4

@pytest.mark.asyncio
async def test_get_log_by_id_invalid(app_with_overrides):
    transport = ASGITransport(app=app_with_overrides)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.get("/api/v1/logs/0")
        assert resp.status_code in (422, 400)

@pytest.mark.asyncio
async def test_event_correlation_prompt(app_with_overrides):
    transport = ASGITransport(app=app_with_overrides)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.post("/api/v1/logs/event_correlation", json={"logs": []})
        assert resp.status_code == 200
        assert "event correlation" in resp.text or resp.text == '"prompt event correlation"'

@pytest.mark.asyncio
async def test_anomaly_detection_prompt(app_with_overrides):
    transport = ASGITransport(app=app_with_overrides)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.post("/api/v1/logs/anomaly_detection", json={"logs": [], "baseline_stats": {}})
        assert resp.status_code == 200
        assert "anomaly detect" in resp.text or resp.text == '"prompt anomaly detect"'

@pytest.mark.asyncio
async def test_pattern_detection_prompt(app_with_overrides):
    transport = ASGITransport(app=app_with_overrides)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.post("/api/v1/logs/pattern_detection", json={"logs": []})
        assert resp.status_code == 200
        assert "pattern detect" in resp.text or resp.text == '"prompt pattern detect"'

@pytest.mark.asyncio
async def test_root_cause_analysis_prompt(app_with_overrides):
    transport = ASGITransport(app=app_with_overrides)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.post("/api/v1/logs/root_cause", json={"logs": []})
        assert resp.status_code == 200
        assert "root cause" in resp.text or resp.text == '"prompt root cause"'

@pytest.mark.asyncio
async def test_error_summarization_prompt(app_with_overrides):
    transport = ASGITransport(app=app_with_overrides)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.post("/api/v1/logs/error_summarization", json={"logs": []})
        assert resp.status_code == 200
        assert "error summary" in resp.text or resp.text == '"prompt error summary"'
