"""Unit tests for health check routes.

This module tests the health check endpoints for the API service.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.api.routes.health import router


class TestHealthRoutes:
    """Test suite for health check routes."""

    @pytest.fixture
    def app(self) -> FastAPI:
        """Create a test FastAPI app with health routes."""
        app = FastAPI()
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
        with patch("src.api.routes.health.get_services_health") as mock_get_health:
            mock_get_health.return_value = {
                "database": True,
                "storage": True,
                "queue": True,
                "vault": True,
                "ollama": True,
            }
            
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
        with patch("src.api.routes.health.get_services_health") as mock_get_health:
            mock_get_health.return_value = {
                "database": True,
                "storage": False,
                "queue": True,
                "vault": False,
                "ollama": True,
            }
            
            response = client.get("/health/services")
            
            assert response.status_code == 200
            data = response.json()
            assert data["database"] is True
            assert data["storage"] is False
            assert data["queue"] is True
            assert data["vault"] is False
            assert data["ollama"] is True

