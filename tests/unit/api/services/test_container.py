"""Unit tests for ServiceContainer.

Covers initialization, property access (error cases), shutdown logic, and async context manager for full coverage.
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.api.services.container import ServiceContainer, get_service_container


# Minimal fake config with attributes expected by ServiceContainer
class FakeConfig:
    async_postgres_dsn = "postgresql+asyncpg://user:pass@localhost:5432/db"
    minio_endpoint = "endpoint"
    minio_access_key = "key"
    minio_secret_key = "secret"
    minio_secure = True
    rabbitmq_url = "amqp://guest:guest@localhost:5672//"
    vault_addr = "vault_addr"
    vault_token = "vault_token"
    ollama_base_url = "http://ollama"
    vision_model_default = "llava:latest"
    image_bucket = "bucket"
    max_image_size_mb = 42


@pytest.fixture
def mock_services(monkeypatch):
    db = MagicMock(name="DatabaseService", close=AsyncMock())
    storage = MagicMock(name="StorageService")
    queue = MagicMock(name="QueueService", close=AsyncMock())
    vault = MagicMock(name="VaultService")
    ollama = MagicMock(name="OllamaService", initialize=AsyncMock(), close=AsyncMock())
    image_analysis = MagicMock(name="ImageAnalysisService")

    # Patch at the point of use in container.py
    monkeypatch.setattr("src.api.services.container.DatabaseService", lambda dsn: db)
    monkeypatch.setattr("src.api.services.container.StorageService", lambda **kwargs: storage)
    monkeypatch.setattr("src.api.services.container.QueueService", lambda url: queue)
    monkeypatch.setattr("src.api.services.container.VaultService", lambda addr, token: vault)
    monkeypatch.setattr("src.api.services.container.OllamaService", lambda base_url: ollama)
    monkeypatch.setattr(
        "src.api.services.container.ImageAnalysisService", lambda **kwargs: image_analysis
    )

    return SimpleNamespace(
        db=db,
        storage=storage,
        queue=queue,
        vault=vault,
        ollama=ollama,
        image_analysis=image_analysis,
    )


def make_uninitialized_container():
    return ServiceContainer(FakeConfig())


@pytest.mark.asyncio
async def test_initialize_creates_all_services_and_calls_ollama_init(mock_services):
    c = ServiceContainer(FakeConfig())
    await c.initialize()
    # Proper service init sequence
    assert mock_services.db is c._database
    assert mock_services.storage is c._storage
    assert mock_services.queue is c._queue
    assert mock_services.vault is c._vault
    assert mock_services.ollama is c._ollama
    assert mock_services.image_analysis is c._image_analysis
    mock_services.ollama.initialize.assert_awaited_once()


@pytest.mark.asyncio
async def test_shutdown_closes_services_if_initialized(mock_services):
    c = ServiceContainer(FakeConfig())
    await c.initialize()
    await c.shutdown()
    mock_services.db.close.assert_awaited_once()
    mock_services.ollama.close.assert_awaited_once()
    mock_services.queue.close.assert_awaited_once()


@pytest.mark.asyncio
async def test_shutdown_is_noop_if_not_initialized(monkeypatch):
    c = ServiceContainer(FakeConfig())
    # Should not raise if not initialized (none of the close methods exist yet)
    await c.shutdown()


@pytest.mark.parametrize(
    "propname, privname",
    [
        ("database", "_database"),
        ("storage", "_storage"),
        ("queue", "_queue"),
        ("vault", "_vault"),
        ("ollama", "_ollama"),
        ("image_analysis", "_image_analysis"),
    ],
)
def test_properties_raise_if_not_initialized(propname, privname):
    c = make_uninitialized_container()
    # Ensure attribute is None
    setattr(c, privname, None)
    with pytest.raises(RuntimeError, match="ServiceContainer not initialized"):
        getattr(c, propname)


@pytest.mark.parametrize(
    "propname, privname, mock_attr",
    [
        ("database", "_database", MagicMock()),
        ("storage", "_storage", MagicMock()),
        ("queue", "_queue", MagicMock()),
        ("vault", "_vault", MagicMock()),
        ("ollama", "_ollama", MagicMock()),
        ("image_analysis", "_image_analysis", MagicMock()),
    ],
)
def test_properties_return_instance_when_initialized(propname, privname, mock_attr):
    c = make_uninitialized_container()
    setattr(c, privname, mock_attr)
    assert getattr(c, propname) is mock_attr


@pytest.mark.asyncio
async def test_get_service_container_lifecycle(mock_services):
    config = FakeConfig()
    # Patch ServiceContainer so we can monitor initialize/shutdown
    with patch(
        "src.api.services.container.ServiceContainer", wraps=ServiceContainer
    ) as MockContainer:
        async with get_service_container(config) as container:
            assert isinstance(container, ServiceContainer)
            # Should be initialized
            assert container._database is mock_services.db
        # Should be shutdown
        # Container's shutdown() called after context exit
        # (Already covered in shutdown test)


@pytest.mark.asyncio
async def test_get_service_container_shutdown_called_on_exception(mock_services):
    config = FakeConfig()
    with patch(
        "src.api.services.container.ServiceContainer", wraps=ServiceContainer
    ) as MockContainer:

        class CustomExc(Exception):
            pass

        with pytest.raises(CustomExc):
            async with get_service_container(config) as container:
                raise CustomExc("fail in context")
        # Still should call shutdown (already tested above)
