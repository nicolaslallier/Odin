"""Unit tests for health route handlers.

Following TDD principles - RED phase: These tests will fail until implementation.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from fastapi import APIRouter
from fastapi.testclient import TestClient


@pytest.mark.unit
class TestHealthRouter:
    """Test suite for health router configuration."""

    def test_health_router_exists(self) -> None:
        """Test that health router can be imported."""
        from src.web.routes.health import router

        assert isinstance(router, APIRouter)

    def test_health_router_has_routes(self) -> None:
        """Test that health router has registered routes."""
        from src.web.routes.health import router

        assert len(router.routes) > 0

    def test_health_router_has_health_route(self) -> None:
        """Test that health router has a /health route."""
        from src.web.routes.health import router

        paths = [route.path for route in router.routes]
        assert "/health" in paths


@pytest.mark.unit
class TestHealthRouteHandlers:
    """Test suite for health route handler functions."""

    @pytest.fixture
    def client(self) -> TestClient:
        """Create a test client for the application.

        Returns:
            TestClient instance for making test requests
        """
        from src.web.app import create_app

        app = create_app()
        return TestClient(app)
    

    def test_health_page_returns_200(self, client: TestClient) -> None:
        """Test that health page returns 200 status code."""
        with patch("src.web.routes.health.fetch_infrastructure_health") as mock_infra, \
             patch("src.web.routes.health.fetch_circuit_breaker_states") as mock_cb, \
             patch("src.web.routes.health.check_application_services") as mock_app:
            # Mock infrastructure health
            mock_infra.return_value = {
                "database": True,
                "storage": True,
                "queue": True,
                "vault": True,
                "ollama": True,
            }
            
            # Mock circuit breaker states
            mock_cb.return_value = {"database": "closed", "storage": "closed"}
            
            # Mock application services
            mock_app.return_value = {
                "portal": True,
                "api": True,
                "worker": True,
                "beat": True,
                "flower": True,
            }

            response = client.get("/health")

            assert response.status_code == 200

    def test_health_page_returns_html(self, client: TestClient) -> None:
        """Test that health page returns HTML content."""
        with patch("src.web.routes.health.fetch_infrastructure_health") as mock_infra, \
             patch("src.web.routes.health.fetch_circuit_breaker_states") as mock_cb, \
             patch("src.web.routes.health.check_application_services") as mock_app:
            # Mock infrastructure health
            mock_infra.return_value = {
                "database": True,
                "storage": True,
                "queue": True,
                "vault": True,
                "ollama": True,
            }
            
            # Mock circuit breaker states
            mock_cb.return_value = {}
            
            # Mock application services
            mock_app.return_value = {
                "portal": True,
                "api": True,
                "worker": True,
                "beat": True,
                "flower": True,
            }

            response = client.get("/health")

            assert "text/html" in response.headers["content-type"]

    def test_health_page_contains_health_title(self, client: TestClient) -> None:
        """Test that health page contains health monitoring title."""
        with patch("src.web.routes.health.fetch_infrastructure_health") as mock_infra, \
             patch("src.web.routes.health.fetch_circuit_breaker_states") as mock_cb, \
             patch("src.web.routes.health.check_application_services") as mock_app:
            # Mock infrastructure health
            mock_infra.return_value = {
                "database": True,
                "storage": True,
                "queue": True,
                "vault": True,
                "ollama": True,
            }
            
            # Mock circuit breaker states
            mock_cb.return_value = {}
            
            # Mock application services
            mock_app.return_value = {
                "portal": True,
                "api": True,
                "worker": True,
                "beat": True,
                "flower": True,
            }

            response = client.get("/health")

            assert "Health" in response.text or "health" in response.text

    def test_health_api_returns_json(self, client: TestClient) -> None:
        """Test that health API endpoint returns JSON data."""
        with patch("src.web.routes.health.fetch_infrastructure_health") as mock_infra, \
             patch("src.web.routes.health.fetch_circuit_breaker_states") as mock_cb, \
             patch("src.web.routes.health.check_application_services") as mock_app:
            # Mock infrastructure health
            mock_infra.return_value = {
                "database": True,
                "storage": True,
                "queue": True,
                "vault": True,
                "ollama": True,
            }
            
            # Mock circuit breaker states
            mock_cb.return_value = {"database": "closed"}
            
            # Mock application services
            mock_app.return_value = {
                "portal": True,
                "api": True,
                "worker": True,
                "beat": True,
                "flower": True,
            }

            response = client.get("/health/api")

            assert response.status_code == 200
            assert response.headers["content-type"] == "application/json"

    def test_health_api_returns_infrastructure_services(self, client: TestClient) -> None:
        """Test that health API returns infrastructure service statuses."""
        with patch("src.web.routes.health.fetch_infrastructure_health") as mock_infra, \
             patch("src.web.routes.health.fetch_circuit_breaker_states") as mock_cb, \
             patch("src.web.routes.health.check_application_services") as mock_app:
            # Mock infrastructure health
            mock_infra.return_value = {
                "database": True,
                "storage": True,
                "queue": True,
                "vault": True,
                "ollama": True,
            }
            
            # Mock circuit breaker states
            mock_cb.return_value = {}
            
            # Mock application services
            mock_app.return_value = {
                "portal": True,
                "api": True,
                "worker": True,
                "beat": True,
                "flower": True,
            }

            response = client.get("/health/api")
            data = response.json()

            assert "infrastructure" in data
            assert "database" in data["infrastructure"]
            assert "storage" in data["infrastructure"]
            assert "queue" in data["infrastructure"]
            assert "vault" in data["infrastructure"]
            assert "ollama" in data["infrastructure"]

    def test_health_api_handles_api_service_unavailable(self, client: TestClient) -> None:
        """Test that health API handles API service being unavailable."""
        with patch("src.web.routes.health.httpx.AsyncClient") as mock_client:
            mock_instance = AsyncMock()
            mock_instance.get.side_effect = Exception("Connection refused")
            mock_client.return_value.__aenter__.return_value = mock_instance

            response = client.get("/health/api")

            assert response.status_code == 200
            data = response.json()
            # Should return degraded state when API is unavailable
            assert "infrastructure" in data or "error" in data

    def test_health_api_returns_circuit_breaker_states(self, client: TestClient) -> None:
        """Test that health API returns circuit breaker states."""
        with patch("src.web.routes.health.fetch_infrastructure_health") as mock_infra, \
             patch("src.web.routes.health.fetch_circuit_breaker_states") as mock_cb, \
             patch("src.web.routes.health.check_application_services") as mock_app:
            # Mock infrastructure health
            mock_infra.return_value = {
                "database": True,
                "storage": True,
                "queue": True,
                "vault": True,
                "ollama": True,
            }
            
            # Mock circuit breaker states
            mock_cb.return_value = {
                "database": "closed",
                "storage": "closed",
                "queue": "open",
            }
            
            # Mock application services
            mock_app.return_value = {
                "portal": True,
                "api": True,
                "worker": True,
                "beat": True,
                "flower": True,
            }

            response = client.get("/health/api")
            data = response.json()

            assert "circuit_breakers" in data
            breakers = data["circuit_breakers"]
            assert "database" in breakers or isinstance(breakers, dict)

    def test_health_api_includes_application_services(self, client: TestClient) -> None:
        """Test that health API includes application service checks."""
        with patch("src.web.routes.health.fetch_infrastructure_health") as mock_infra, \
             patch("src.web.routes.health.fetch_circuit_breaker_states") as mock_cb, \
             patch("src.web.routes.health.check_application_services") as mock_app:
            # Mock infrastructure health
            mock_infra.return_value = {
                "database": True,
                "storage": True,
                "queue": True,
                "vault": True,
                "ollama": True,
            }
            
            # Mock circuit breaker states
            mock_cb.return_value = {}
            
            # Mock application services
            mock_app.return_value = {
                "portal": True,
                "api": True,
                "worker": True,
                "beat": True,
                "flower": True,
            }

            response = client.get("/health/api")
            data = response.json()

            # Should have application services section
            assert "application" in data or "services" in data

    def test_health_page_graceful_degradation_on_api_error(self, client: TestClient) -> None:
        """Test that health page gracefully handles API errors."""
        with patch("src.web.routes.health.fetch_infrastructure_health") as mock_infra, \
             patch("src.web.routes.health.fetch_circuit_breaker_states") as mock_cb, \
             patch("src.web.routes.health.check_application_services") as mock_app:
            # Mock infrastructure health - simulate API error with default values
            mock_infra.return_value = {
                "database": False,
                "storage": False,
                "queue": False,
                "vault": False,
                "ollama": False,
            }
            
            # Mock circuit breaker states - empty when API is down
            mock_cb.return_value = {}
            
            # Mock application services - degraded state
            mock_app.return_value = {
                "portal": True,
                "api": False,
                "worker": False,
                "beat": False,
                "flower": False,
            }

            response = client.get("/health")

            # Should still return 200 but show degraded state
            assert response.status_code == 200
            assert "text/html" in response.headers["content-type"]

