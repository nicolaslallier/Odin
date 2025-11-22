"""Unit tests for health check routes.

This module tests the health check endpoints for the API service.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

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

    @pytest.mark.asyncio
    async def test_health_services_endpoint_all_healthy(self, client: TestClient) -> None:
        """Test /health/services endpoint when all services are healthy."""
        with patch("src.api.routes.health.DatabaseService") as mock_db, \
             patch("src.api.routes.health.StorageService") as mock_storage, \
             patch("src.api.routes.health.QueueService") as mock_queue, \
             patch("src.api.routes.health.VaultService") as mock_vault, \
             patch("src.api.routes.health.OllamaService") as mock_ollama:
            
            # Mock all service health checks
            mock_db_instance = AsyncMock()
            mock_db_instance.health_check = AsyncMock(return_value=True)
            mock_db.return_value = mock_db_instance
            
            mock_storage_instance = MagicMock()
            mock_storage_instance.health_check = MagicMock(return_value=True)
            mock_storage.return_value = mock_storage_instance
            
            mock_queue_instance = MagicMock()
            mock_queue_instance.health_check = MagicMock(return_value=True)
            mock_queue.return_value = mock_queue_instance
            
            mock_vault_instance = MagicMock()
            mock_vault_instance.health_check = MagicMock(return_value=True)
            mock_vault.return_value = mock_vault_instance
            
            mock_ollama_instance = AsyncMock()
            mock_ollama_instance.health_check = AsyncMock(return_value=True)
            mock_ollama.return_value = mock_ollama_instance
            
            response = client.get("/health/services")
            
            assert response.status_code == 200
            data = response.json()
            assert data["database"] is True
            assert data["storage"] is True
            assert data["queue"] is True
            assert data["vault"] is True
            assert data["ollama"] is True

    @pytest.mark.asyncio
    async def test_health_services_endpoint_some_unhealthy(self, client: TestClient) -> None:
        """Test /health/services endpoint when some services are unhealthy."""
        with patch("src.api.routes.health.DatabaseService") as mock_db, \
             patch("src.api.routes.health.StorageService") as mock_storage, \
             patch("src.api.routes.health.QueueService") as mock_queue, \
             patch("src.api.routes.health.VaultService") as mock_vault, \
             patch("src.api.routes.health.OllamaService") as mock_ollama:
            
            # Mock service health checks with some failures
            mock_db_instance = AsyncMock()
            mock_db_instance.health_check = AsyncMock(return_value=True)
            mock_db.return_value = mock_db_instance
            
            mock_storage_instance = MagicMock()
            mock_storage_instance.health_check = MagicMock(return_value=False)
            mock_storage.return_value = mock_storage_instance
            
            mock_queue_instance = MagicMock()
            mock_queue_instance.health_check = MagicMock(return_value=True)
            mock_queue.return_value = mock_queue_instance
            
            mock_vault_instance = MagicMock()
            mock_vault_instance.health_check = MagicMock(return_value=False)
            mock_vault.return_value = mock_vault_instance
            
            mock_ollama_instance = AsyncMock()
            mock_ollama_instance.health_check = AsyncMock(return_value=True)
            mock_ollama.return_value = mock_ollama_instance
            
            response = client.get("/health/services")
            
            assert response.status_code == 200
            data = response.json()
            assert data["database"] is True
            assert data["storage"] is False
            assert data["queue"] is True
            assert data["vault"] is False
            assert data["ollama"] is True

