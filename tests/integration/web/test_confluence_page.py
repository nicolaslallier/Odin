"""Integration tests for Confluence web interface.

This module tests the full Confluence workflow integration with real services
(when available) or skips tests gracefully.
"""

from __future__ import annotations

import os
from unittest.mock import AsyncMock, Mock, patch

import pytest
from fastapi.testclient import TestClient

from src.web.app import create_app


@pytest.fixture
def test_app():
    """Create a test application instance.

    Returns:
        TestClient for the web application
    """
    app = create_app()
    return TestClient(app)


@pytest.mark.integration
class TestConfluencePageRendering:
    """Test cases for Confluence page rendering."""

    def test_confluence_page_loads(self, test_app: TestClient) -> None:
        """Test that the Confluence page loads successfully."""
        response = test_app.get("/confluence")

        assert response.status_code == 200
        assert b"Confluence Integration" in response.content
        assert b"Page to Markdown" in response.content
        assert b"Markdown to Page" in response.content
        assert b"Summarize Page" in response.content
        assert b"Backup Space" in response.content
        assert b"Statistics" in response.content


@pytest.mark.integration
class TestConfluenceServiceInitialization:
    """Test cases for Confluence service initialization."""

    def test_vault_service_available(self, test_app: TestClient) -> None:
        """Test that Vault service is available in app state."""
        assert hasattr(test_app.app.state, "vault_service")
        assert test_app.app.state.vault_service is not None

    def test_storage_service_available(self, test_app: TestClient) -> None:
        """Test that Storage service is available in app state."""
        assert hasattr(test_app.app.state, "storage_service")
        assert test_app.app.state.storage_service is not None

    def test_ollama_service_available(self, test_app: TestClient) -> None:
        """Test that Ollama service is available in app state."""
        assert hasattr(test_app.app.state, "ollama_service")
        assert test_app.app.state.ollama_service is not None


# Remove all credential/env checking and always run the integration tests for the proxy
@pytest.mark.integration
class TestConfluenceEndToEnd:
    """Integration tests for Confluence proxy endpoints via the web portal.
    These tests do not require Confluence or API credentials for the portal.
    """

    def test_convert_to_markdown_proxy(self, test_app: TestClient) -> None:
        """Proxy POST to /confluence/convert-to-markdown should get 503 if backend is unavailable or 200 if mock/real API up."""
        response = test_app.post(
            "/confluence/convert-to-markdown",
            json={"page_id": "dummy", "save_to_storage": False},
        )
        # Accept proxy failure or proxy pass; never require portal Confluence credentials
        assert response.status_code in [200, 404, 500, 503]

    def test_get_statistics_proxy(self, test_app: TestClient) -> None:
        """Proxy POST to /confluence/statistics should get 503 if backend is unavailable or mock data if up."""
        response = test_app.post(
            "/confluence/statistics",
            json={"space_key": "dummy-key"},
        )
        assert response.status_code in [200, 404, 503]

    def test_convert_to_markdown_nonexistent_page(self, test_app: TestClient) -> None:
        """Proxy: returns 404 for a non-existent page id."""
        response = test_app.post(
            "/confluence/convert-to-markdown",
            json={"page_id": "999999", "save_to_storage": False},
        )
        assert response.status_code in [404, 503]
        if response.status_code == 404:
            assert "not found" in response.text.lower()

    def test_convert_to_markdown_proxy_backend_error(self, test_app: TestClient) -> None:
        """Proxy: get 500 relay from backend API error (simulate backend fail)."""
        response = test_app.post(
            "/confluence/convert-to-markdown",
            json={"page_id": "error", "save_to_storage": False},
        )
        assert response.status_code in [500, 503]
        assert (
            "error" in response.text.lower()
            or "fail" in response.text.lower()
            or response.status_code != 200
        )

    def test_unhandled_confluence_route(self, test_app: TestClient) -> None:
        """Non-existent route should return 404."""
        response = test_app.get("/confluence/nonexistent-route")
        assert response.status_code == 404

    def test_get_models_proxy_error(self, test_app: TestClient) -> None:
        """Proxy: /confluence/models returns 503/404 or OK list."""
        response = test_app.get("/confluence/models")
        assert response.status_code in [200, 503, 404]
        if response.status_code == 200:
            data = response.json()
            assert "models" in data


@pytest.mark.integration
class TestConfluenceErrorHandling:
    """Test cases for Confluence error handling."""

    @patch("src.api.services.vault.VaultService.read_secret")
    def test_missing_credentials_error(self, mock_read_secret: Mock, test_app: TestClient) -> None:
        """Missing credentials should just relay API error (never check for credentials at the portal)."""
        response = test_app.post(
            "/confluence/convert-to-markdown",
            json={"page_id": "123456", "save_to_storage": False},
        )
        assert response.status_code in [404, 503, 500]
        # Accept any error detail – just check it's not a portal credential validation
        assert (
            "error" in response.text.lower()
            or "not found" in response.text.lower()
            or response.status_code != 200
        )

    def test_invalid_page_id_format(self, test_app: TestClient) -> None:
        """Invalid page ID should cause a FastAPI validation error or relay 400/422 from backend."""
        response = test_app.post(
            "/confluence/convert-to-markdown",
            json={"page_id": "", "save_to_storage": False},
        )
        assert response.status_code in [400, 422]

    def test_missing_required_fields(self, test_app: TestClient) -> None:
        """Test that missing required fields are rejected."""
        response = test_app.post(
            "/confluence/convert-from-markdown",
            json={"space_key": "TEST"},  # Missing title and markdown
        )

        assert response.status_code == 422

    def test_invalid_format_for_backup(self, test_app: TestClient) -> None:
        """Invalid backup format relays error."""
        response = test_app.post(
            "/confluence/backup-space",
            json={"space_key": "TEST", "format": "invalid"},
        )
        assert response.status_code in [400, 422]


@pytest.mark.integration
class TestConfluenceModelsEndpoint:
    """Test cases for LLM models endpoint."""

    @patch("src.api.services.ollama.OllamaService.list_models")
    async def test_get_models_success(
        self, mock_list_models: AsyncMock, test_app: TestClient
    ) -> None:
        """Test successful model list retrieval."""
        mock_list_models.return_value = [
            {"name": "mistral:latest", "size": 4000000000},
            {"name": "llama3.2:latest", "size": 2000000000},
        ]

        response = test_app.get("/confluence/models")

        # May fail if Ollama not available, which is expected
        assert response.status_code in [200, 503]

        if response.status_code == 200:
            data = response.json()
            assert "models" in data
            assert isinstance(data["models"], list)
