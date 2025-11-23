"""Unit tests for health check routes.

This module tests the health check endpoints for the API service.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.api.config import APIConfig
from src.api.routes.health import router


class TestHealthRoutes:
    """Test suite for health check routes."""

    @pytest.fixture
    def mock_config(self) -> APIConfig:
        """Create a mock configuration."""
        return APIConfig(
            host="0.0.0.0",
            port=8001,
            postgres_dsn="postgresql://test:test@localhost:5432/test",
            minio_endpoint="minio:9000",
            minio_access_key="minioadmin",
            minio_secret_key="minioadmin",
            rabbitmq_url="amqp://test:test@localhost:5672/",
            vault_addr="http://vault:8200",
            vault_token="test-token",
            ollama_base_url="http://ollama:11434",
        )

    @pytest.fixture
    def app(self, mock_config: APIConfig) -> FastAPI:
        """Create a test FastAPI app with health routes."""
        app = FastAPI()
        app.state.config = mock_config
        app.include_router(router)
        return app

    @pytest.fixture
    def client(self, app: FastAPI) -> TestClient:
        """Create a test client."""
        return TestClient(app)

    def test_health_endpoint_returns_healthy(self, client: TestClient) -> None:
        """Test /health endpoint returns healthy status."""
        response = client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "odin-api"

    def test_health_services_endpoint_all_healthy(self, client: TestClient, app: FastAPI) -> None:
        """Test /health/services endpoint when all services are healthy."""
        from src.api.routes.health import get_container

        # Create mock container with all services healthy
        mock_container = MagicMock()

        # All health_check methods must be AsyncMock since they're awaited
        mock_db = MagicMock()
        mock_db.health_check = AsyncMock(return_value=True)
        mock_container.database = mock_db

        mock_storage = MagicMock()
        mock_storage.health_check = AsyncMock(return_value=True)
        mock_container.storage = mock_storage

        mock_queue = MagicMock()
        mock_queue.health_check = AsyncMock(return_value=True)
        mock_container.queue = mock_queue

        mock_vault = MagicMock()
        mock_vault.health_check = AsyncMock(return_value=True)
        mock_container.vault = mock_vault

        mock_ollama = MagicMock()
        mock_ollama.health_check = AsyncMock(return_value=True)
        mock_container.ollama = mock_ollama

        # Override dependency
        app.dependency_overrides[get_container] = lambda: mock_container

        try:
            response = client.get("/health/services")

            assert response.status_code == 200
            data = response.json()
            assert data["database"] is True
            assert data["storage"] is True
            assert data["queue"] is True
            assert data["vault"] is True
            assert data["ollama"] is True
        finally:
            app.dependency_overrides.clear()

    def test_health_services_endpoint_some_unhealthy(
        self, client: TestClient, app: FastAPI
    ) -> None:
        """Test /health/services endpoint when some services are unhealthy."""
        # Clear cache to avoid interference from previous test
        import asyncio

        from src.api.routes.health import get_container
        from src.api.services.cache import get_cache

        cache = get_cache()
        asyncio.run(cache.delete("health:services"))

        # Create mock container with some services unhealthy
        mock_container = MagicMock()

        # All health_check methods must be AsyncMock since they're awaited
        mock_db = MagicMock()
        mock_db.health_check = AsyncMock(return_value=True)
        mock_container.database = mock_db

        mock_storage = MagicMock()
        mock_storage.health_check = AsyncMock(return_value=False)
        mock_container.storage = mock_storage

        mock_queue = MagicMock()
        mock_queue.health_check = AsyncMock(return_value=True)
        mock_container.queue = mock_queue

        mock_vault = MagicMock()
        mock_vault.health_check = AsyncMock(return_value=False)
        mock_container.vault = mock_vault

        mock_ollama = MagicMock()
        mock_ollama.health_check = AsyncMock(return_value=True)
        mock_container.ollama = mock_ollama

        # Override dependency
        app.dependency_overrides[get_container] = lambda: mock_container

        try:
            response = client.get("/health/services")

            assert response.status_code == 200
            data = response.json()
            assert data["database"] is True
            assert data["storage"] is False
            assert data["queue"] is True
            assert data["vault"] is False
            assert data["ollama"] is True
        finally:
            app.dependency_overrides.clear()
