"""Integration tests for health monitoring page.

These tests verify that the health monitoring page renders correctly and
displays all required information.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient


@pytest.mark.integration
class TestHealthPageRendering:
    """Integration test suite for health page rendering."""

    @pytest.fixture
    def client(self) -> TestClient:
        """Create a test client for testing health page.

        Returns:
            TestClient instance for making test requests
        """
        from src.web.app import create_app

        app = create_app()
        return TestClient(app)

    def test_health_page_renders_successfully(self, client: TestClient) -> None:
        """Test that health page renders without errors."""
        with patch("src.web.routes.health.httpx.AsyncClient") as mock_client:
            mock_instance = AsyncMock()
            mock_instance.get.side_effect = [
                AsyncMock(
                    status_code=200,
                    json=AsyncMock(
                        return_value={
                            "database": True,
                            "storage": True,
                            "queue": True,
                            "vault": True,
                            "ollama": True,
                        }
                    ),
                ),
                AsyncMock(
                    status_code=200,
                    json=AsyncMock(return_value={"database": "closed"}),
                ),
            ]
            mock_client.return_value.__aenter__.return_value = mock_instance

            response = client.get("/health-page")

            assert response.status_code == 200
            assert "text/html" in response.headers["content-type"]

    def test_health_page_uses_base_template(self, client: TestClient) -> None:
        """Test that health page extends the base template."""
        with patch("src.web.routes.health.httpx.AsyncClient") as mock_client:
            mock_instance = AsyncMock()
            mock_instance.get.side_effect = [
                AsyncMock(
                    status_code=200,
                    json=AsyncMock(
                        return_value={
                            "database": True,
                            "storage": True,
                            "queue": True,
                            "vault": True,
                            "ollama": True,
                        }
                    ),
                ),
                AsyncMock(
                    status_code=200,
                    json=AsyncMock(return_value={}),
                ),
            ]
            mock_client.return_value.__aenter__.return_value = mock_instance

            response = client.get("/health-page")
            content = response.text

            # Check for base template elements
            assert "Odin" in content
            assert "<header>" in content or "<nav>" in content
            assert "<footer>" in content

    def test_health_page_displays_infrastructure_section(self, client: TestClient) -> None:
        """Test that health page displays infrastructure services section."""
        with patch("src.web.routes.health.httpx.AsyncClient") as mock_client:
            mock_instance = AsyncMock()
            mock_instance.get.side_effect = [
                AsyncMock(
                    status_code=200,
                    json=AsyncMock(
                        return_value={
                            "database": True,
                            "storage": True,
                            "queue": True,
                            "vault": True,
                            "ollama": True,
                        }
                    ),
                ),
                AsyncMock(
                    status_code=200,
                    json=AsyncMock(return_value={}),
                ),
            ]
            mock_client.return_value.__aenter__.return_value = mock_instance

            response = client.get("/health-page")
            content = response.text

            assert "Infrastructure" in content
            assert "database" in content.lower()
            assert "storage" in content.lower()
            assert "queue" in content.lower()

    def test_health_page_displays_application_section(self, client: TestClient) -> None:
        """Test that health page displays application services section."""
        with patch("src.web.routes.health.httpx.AsyncClient") as mock_client:
            mock_instance = AsyncMock()
            mock_instance.get.side_effect = [
                AsyncMock(
                    status_code=200,
                    json=AsyncMock(
                        return_value={
                            "database": True,
                            "storage": True,
                            "queue": True,
                            "vault": True,
                            "ollama": True,
                        }
                    ),
                ),
                AsyncMock(
                    status_code=200,
                    json=AsyncMock(return_value={}),
                ),
            ]
            mock_client.return_value.__aenter__.return_value = mock_instance

            response = client.get("/health-page")
            content = response.text

            assert "Application" in content
            assert "portal" in content.lower() or "Portal" in content

    def test_health_page_displays_circuit_breakers_section(self, client: TestClient) -> None:
        """Test that health page displays circuit breakers section."""
        with patch("src.web.routes.health.httpx.AsyncClient") as mock_client:
            mock_instance = AsyncMock()
            mock_instance.get.side_effect = [
                AsyncMock(
                    status_code=200,
                    json=AsyncMock(
                        return_value={
                            "database": True,
                            "storage": True,
                            "queue": True,
                            "vault": True,
                            "ollama": True,
                        }
                    ),
                ),
                AsyncMock(
                    status_code=200,
                    json=AsyncMock(
                        return_value={
                            "database": "closed",
                            "storage": "closed",
                            "queue": "open",
                        }
                    ),
                ),
            ]
            mock_client.return_value.__aenter__.return_value = mock_instance

            response = client.get("/health-page")
            content = response.text

            assert "Circuit Breaker" in content

    def test_health_page_has_refresh_controls(self, client: TestClient) -> None:
        """Test that health page includes refresh controls."""
        with patch("src.web.routes.health.httpx.AsyncClient") as mock_client:
            mock_instance = AsyncMock()
            mock_instance.get.side_effect = [
                AsyncMock(
                    status_code=200,
                    json=AsyncMock(
                        return_value={
                            "database": True,
                            "storage": True,
                            "queue": True,
                            "vault": True,
                            "ollama": True,
                        }
                    ),
                ),
                AsyncMock(
                    status_code=200,
                    json=AsyncMock(return_value={}),
                ),
            ]
            mock_client.return_value.__aenter__.return_value = mock_instance

            response = client.get("/health-page")
            content = response.text

            assert "refresh" in content.lower()
            assert "auto-refresh" in content.lower() or "Auto-refresh" in content

    def test_health_page_displays_last_updated_time(self, client: TestClient) -> None:
        """Test that health page shows last updated timestamp."""
        with patch("src.web.routes.health.httpx.AsyncClient") as mock_client:
            mock_instance = AsyncMock()
            mock_instance.get.side_effect = [
                AsyncMock(
                    status_code=200,
                    json=AsyncMock(
                        return_value={
                            "database": True,
                            "storage": True,
                            "queue": True,
                            "vault": True,
                            "ollama": True,
                        }
                    ),
                ),
                AsyncMock(
                    status_code=200,
                    json=AsyncMock(return_value={}),
                ),
            ]
            mock_client.return_value.__aenter__.return_value = mock_instance

            response = client.get("/health-page")
            content = response.text

            assert "Last updated" in content or "last updated" in content

    def test_health_page_includes_javascript(self, client: TestClient) -> None:
        """Test that health page includes JavaScript for auto-refresh."""
        with patch("src.web.routes.health.httpx.AsyncClient") as mock_client:
            mock_instance = AsyncMock()
            mock_instance.get.side_effect = [
                AsyncMock(
                    status_code=200,
                    json=AsyncMock(
                        return_value={
                            "database": True,
                            "storage": True,
                            "queue": True,
                            "vault": True,
                            "ollama": True,
                        }
                    ),
                ),
                AsyncMock(
                    status_code=200,
                    json=AsyncMock(return_value={}),
                ),
            ]
            mock_client.return_value.__aenter__.return_value = mock_instance

            response = client.get("/health-page")
            content = response.text

            assert "/static/js/health.js" in content or "health.js" in content

    def test_health_page_shows_service_status_badges(self, client: TestClient) -> None:
        """Test that health page displays status badges for services."""
        with patch("src.web.routes.health.httpx.AsyncClient") as mock_client:
            mock_instance = AsyncMock()
            mock_instance.get.side_effect = [
                AsyncMock(
                    status_code=200,
                    json=AsyncMock(
                        return_value={
                            "database": True,
                            "storage": False,
                            "queue": True,
                            "vault": True,
                            "ollama": False,
                        }
                    ),
                ),
                AsyncMock(
                    status_code=200,
                    json=AsyncMock(return_value={}),
                ),
            ]
            mock_client.return_value.__aenter__.return_value = mock_instance

            response = client.get("/health-page")
            content = response.text

            # Should show both healthy and unhealthy statuses
            assert "Healthy" in content
            assert "Unhealthy" in content

    def test_health_page_has_proper_html_structure(self, client: TestClient) -> None:
        """Test that health page has proper semantic HTML structure."""
        with patch("src.web.routes.health.httpx.AsyncClient") as mock_client:
            mock_instance = AsyncMock()
            mock_instance.get.side_effect = [
                AsyncMock(
                    status_code=200,
                    json=AsyncMock(
                        return_value={
                            "database": True,
                            "storage": True,
                            "queue": True,
                            "vault": True,
                            "ollama": True,
                        }
                    ),
                ),
                AsyncMock(
                    status_code=200,
                    json=AsyncMock(return_value={}),
                ),
            ]
            mock_client.return_value.__aenter__.return_value = mock_instance

            response = client.get("/health-page")
            content = response.text

            assert "<!DOCTYPE html>" in content or "<html" in content
            assert "<head>" in content
            assert "<body>" in content
            assert "</html>" in content

    def test_health_api_endpoint_returns_json(self, client: TestClient) -> None:
        """Test that /health/api endpoint returns JSON data."""
        with patch("src.web.routes.health.httpx.AsyncClient") as mock_client:
            mock_instance = AsyncMock()
            mock_instance.get.side_effect = [
                AsyncMock(
                    status_code=200,
                    json=AsyncMock(
                        return_value={
                            "database": True,
                            "storage": True,
                            "queue": True,
                            "vault": True,
                            "ollama": True,
                        }
                    ),
                ),
                AsyncMock(
                    status_code=200,
                    json=AsyncMock(return_value={"database": "closed"}),
                ),
            ]
            mock_client.return_value.__aenter__.return_value = mock_instance

            response = client.get("/health/api")

            assert response.status_code == 200
            assert response.headers["content-type"] == "application/json"
            data = response.json()
            assert "infrastructure" in data
            assert "application" in data

    def test_health_page_no_template_errors(self, client: TestClient) -> None:
        """Test that there are no template rendering errors."""
        with patch("src.web.routes.health.httpx.AsyncClient") as mock_client:
            mock_instance = AsyncMock()
            mock_instance.get.side_effect = [
                AsyncMock(
                    status_code=200,
                    json=AsyncMock(
                        return_value={
                            "database": True,
                            "storage": True,
                            "queue": True,
                            "vault": True,
                            "ollama": True,
                        }
                    ),
                ),
                AsyncMock(
                    status_code=200,
                    json=AsyncMock(return_value={}),
                ),
            ]
            mock_client.return_value.__aenter__.return_value = mock_instance

            response = client.get("/health-page")
            content = response.text

            # Check for common template error indicators
            assert "TemplateNotFound" not in content
            assert "UndefinedError" not in content
            # Allow template tags in script sections
            lines = content.split("\n")
            for line in lines:
                if "<script>" not in line and "</script>" not in line:
                    # Unrendered Jinja variables shouldn't exist outside scripts
                    if "{{ " in line:
                        assert "url_for" not in line or "static" in line

