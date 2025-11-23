"""Unit tests for Confluence web routes.

This module tests the web routes for the Confluence integration interface,
including page rendering and all API endpoints.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.api.exceptions import (
    ConfluenceError,
    ResourceNotFoundError,
    ServiceUnavailableError,
)


@pytest.fixture
def mock_confluence_service() -> MagicMock:
    """Create a mock Confluence service.

    Returns:
        MagicMock for Confluence service
    """
    service = MagicMock()
    service.initialize = AsyncMock()
    service.close = AsyncMock()
    service.get_page_by_id = AsyncMock(
        return_value={
            "id": "123456",
            "title": "Test Page",
            "body": {"storage": {"value": "<p>Test content</p>"}},
        }
    )
    service.convert_page_to_markdown = AsyncMock(return_value="# Test Page\n\nTest content")
    service.convert_markdown_to_storage = Mock(return_value="<h1>Test Page</h1><p>Test content</p>")
    service.create_or_update_page = AsyncMock(
        return_value={
            "id": "789012",
            "title": "New Page",
            "_links": {"webui": "/spaces/TEST/pages/789012/New+Page"},
        }
    )
    service.backup_space = AsyncMock(
        return_value=[
            {"id": "111", "title": "Page 1", "body": {"storage": {"value": "<p>Content 1</p>"}}},
            {"id": "222", "title": "Page 2", "body": {"storage": {"value": "<p>Content 2</p>"}}},
        ]
    )
    service.get_space_statistics = AsyncMock(
        return_value={
            "space_key": "TEST",
            "space_name": "Test Space",
            "total_pages": 10,
            "total_size_bytes": 5000,
            "contributors": ["User 1", "User 2"],
            "last_updated": "2025-01-15T10:00:00.000Z",
        }
    )
    service.health_check = AsyncMock(return_value=True)
    return service


@pytest.fixture
def mock_vault_service() -> MagicMock:
    """Create a mock Vault service.

    Returns:
        MagicMock for Vault service
    """
    service = MagicMock()
    service.read_secret = Mock(
        return_value={
            "base_url": "https://test.atlassian.net/wiki",
            "email": "test@example.com",
            "api_token": "test-token-123",
        }
    )
    return service


@pytest.fixture
def mock_storage_service() -> MagicMock:
    """Create a mock Storage service.

    Returns:
        MagicMock for Storage service
    """
    service = MagicMock()
    service.bucket_exists = Mock(return_value=True)
    service.create_bucket = Mock()
    service.upload_file = Mock()
    return service


@pytest.fixture
def mock_ollama_service() -> MagicMock:
    """Create a mock Ollama service.

    Returns:
        MagicMock for Ollama service
    """
    service = MagicMock()
    service.list_models = AsyncMock(
        return_value=[
            {"name": "mistral:latest", "size": 4000000000},
            {"name": "llama3.2:latest", "size": 2000000000},
        ]
    )
    service.generate_text = AsyncMock(return_value="This is a summary of the page content.")
    service.pull_model = AsyncMock(return_value=True)
    return service


@pytest.fixture
def app_with_mocks(
    mock_confluence_service: MagicMock,
    mock_vault_service: MagicMock,
    mock_storage_service: MagicMock,
    mock_ollama_service: MagicMock,
) -> FastAPI:
    """Create FastAPI app with mocked dependencies.

    Args:
        mock_confluence_service: Mock Confluence service
        mock_vault_service: Mock Vault service
        mock_storage_service: Mock Storage service
        mock_ollama_service: Mock Ollama service

    Returns:
        FastAPI application with mocked dependencies
    """
    from fastapi.templating import Jinja2Templates

    from src.web.config import WebConfig
    from src.web.routes.confluence import router

    app = FastAPI()

    # Set up app state
    app.state.config = WebConfig(
        host="127.0.0.1",
        port=8000,
        api_base_url="http://localhost:8001",
    )

    # Set up templates
    templates_dir = Path(__file__).parent.parent.parent.parent / "src" / "web" / "templates"
    app.state.templates = Jinja2Templates(directory=str(templates_dir))

    # Mount static files for tests
    static_dir = Path(__file__).parent.parent.parent.parent / "src" / "web" / "static"
    static_dir.mkdir(parents=True, exist_ok=True)
    from fastapi.staticfiles import StaticFiles

    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

    # Set up services
    app.state.confluence_service = mock_confluence_service
    app.state.vault_service = mock_vault_service
    app.state.storage_service = mock_storage_service
    app.state.ollama_service = mock_ollama_service

    app.include_router(router)

    return app


@pytest.fixture
def client(app_with_mocks: FastAPI) -> TestClient:
    """Create a test client.

    Args:
        app_with_mocks: FastAPI application with mocked services

    Returns:
        TestClient instance
    """
    return TestClient(app_with_mocks)


@pytest.fixture(autouse=True, scope="module")
def patch_httpx_confluence_success():
    """
    Automatically patch httpx.AsyncClient post/get to simulate Odin API responses for Confluence routes.
    This prevents real HTTP calls in tests and allows production proxy logic to be exercised.
    """

    def make_response(status_code, json_dict):
        resp = Mock()
        resp.status_code = status_code
        resp.is_success = status_code >= 200 and status_code < 300
        resp.json = lambda: json_dict
        return resp

    async def post_side_effect(url, *args, **kwargs):
        if url.endswith("/confluence/convert-to-markdown"):
            body = kwargs.get("json", {})
            page_id = body.get("page_id")
            if page_id == "999999":  # Not found test path
                return make_response(404, {"detail": "Page not found"})
            elif page_id == "error":  # Service error
                return make_response(503, {"detail": "Service unavailable"})
            else:
                return make_response(
                    200, {"markdown": "# Test Page\n\nTest content", "saved_path": None}
                )
        if url.endswith("/confluence/convert-from-markdown"):
            body = kwargs.get("json", {})
            if body.get("title") == "error":
                return make_response(500, {"detail": "Failed to create page"})
            else:
                return make_response(
                    200,
                    {
                        "page_id": "789012",
                        "title": body.get("title", "New Page"),
                        "url": "https://wiki/space/789012",
                    },
                )
        if url.endswith("/confluence/summarize"):
            return make_response(
                200,
                {"summary": "This is a summary of the page content.", "page_title": "Test Page"},
            )
        if url.endswith("/confluence/backup-space"):
            # Simulate minimal success for backup
            return make_response(
                200, {"bucket": "confluence-backups", "path": "path/to/backup.zip", "page_count": 2}
            )
        if url.endswith("/confluence/statistics"):
            return make_response(
                200,
                {
                    "space_key": "TEST",
                    "space_name": "Test Space",
                    "total_pages": 10,
                    "total_size_bytes": 5000,
                    "contributors": ["User 1", "User 2"],
                    "last_updated": "2025-01-15T10:00:00.000Z",
                },
            )
        # Default to 503 for unsupported paths
        return make_response(503, {"detail": "Unknown API path (test)"})

    async def get_side_effect(url, *args, **kwargs):
        if url.endswith("/confluence/models"):
            return make_response(
                200,
                {
                    "models": [
                        {"name": "mistral:latest", "size": 4000000000},
                        {"name": "llama3.2:latest", "size": 2000000000},
                    ]
                },
            )
        return make_response(503, {"detail": "Unknown API path (test)"})

    with patch("httpx.AsyncClient") as mock_ac:
        mock_client = Mock()
        mock_client.post = AsyncMock(side_effect=post_side_effect)
        mock_client.get = AsyncMock(side_effect=get_side_effect)
        mock_ac.return_value.__aenter__.return_value = mock_client
        yield


@pytest.mark.unit
class TestConfluencePageEndpoint:
    """Test cases for GET /confluence endpoint."""

    def test_get_confluence_page(self, client: TestClient) -> None:
        """Test rendering the Confluence interface page."""
        response = client.get("/confluence")

        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]
        assert b"Confluence" in response.content


@pytest.mark.unit
class TestConvertToMarkdownEndpoint:
    """Test cases for POST /confluence/convert-to-markdown endpoint."""

    def test_convert_to_markdown_success(
        self, client: TestClient, mock_confluence_service: MagicMock
    ) -> None:
        """Test successful page to Markdown conversion."""
        response = client.post(
            "/confluence/convert-to-markdown",
            json={"page_id": "123456", "save_to_storage": False},
        )
        assert response.status_code == 200
        result = response.json()
        assert result["markdown"] == "# Test Page\n\nTest content"
        assert result["saved_path"] is None
        # Proxy mode: do not check mock_confluence_service was called (it's never used)

    def test_convert_to_markdown_with_storage(
        self,
        client: TestClient,
        mock_confluence_service: MagicMock,
        mock_storage_service: MagicMock,
    ) -> None:
        """Test conversion with saving to MinIO storage."""
        response = client.post(
            "/confluence/convert-to-markdown",
            json={"page_id": "123456", "save_to_storage": True},
        )
        assert response.status_code == 200
        result = response.json()
        assert result["markdown"] == "# Test Page\n\nTest content"
        assert result["saved_path"] is not None
        assert "confluence-markdown" in result["saved_path"]
        # Proxy mode: do not check mock_storage_service was called

    def test_convert_to_markdown_missing_page_id(self, client: TestClient) -> None:
        """Test conversion without page_id returns error."""
        response = client.post(
            "/confluence/convert-to-markdown",
            json={"save_to_storage": False},
        )

        assert response.status_code == 422  # Validation error

    def test_convert_to_markdown_page_not_found(
        self, client: TestClient, mock_confluence_service: MagicMock
    ) -> None:
        """Test conversion with non-existent page."""
        mock_confluence_service.convert_page_to_markdown.side_effect = ResourceNotFoundError(
            "Page not found", {"page_id": "999999"}
        )

        response = client.post(
            "/confluence/convert-to-markdown",
            json={"page_id": "999999", "save_to_storage": False},
        )

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    def test_convert_to_markdown_service_error(
        self, client: TestClient, mock_confluence_service: MagicMock
    ) -> None:
        """Test conversion with service unavailable."""
        mock_confluence_service.convert_page_to_markdown.side_effect = ServiceUnavailableError(
            "Service unavailable"
        )

        response = client.post(
            "/confluence/convert-to-markdown",
            json={"page_id": "123456", "save_to_storage": False},
        )

        assert response.status_code == 503


@pytest.mark.unit
class TestConvertFromMarkdownEndpoint:
    """Test cases for POST /confluence/convert-from-markdown endpoint."""

    def test_convert_from_markdown_success(
        self, client: TestClient, mock_confluence_service: MagicMock
    ) -> None:
        """Test successful Markdown to page conversion."""
        response = client.post(
            "/confluence/convert-from-markdown",
            json={
                "space_key": "TEST",
                "title": "New Page",
                "markdown": "# Heading\n\nParagraph text",
                "parent_id": None,
            },
        )

        assert response.status_code == 200
        result = response.json()
        assert result["page_id"] == "789012"
        assert result["title"] == "New Page"
        assert "url" in result
        mock_confluence_service.create_or_update_page.assert_called_once()

    def test_convert_from_markdown_with_parent(
        self, client: TestClient, mock_confluence_service: MagicMock
    ) -> None:
        """Test conversion with parent page."""
        response = client.post(
            "/confluence/convert-from-markdown",
            json={
                "space_key": "TEST",
                "title": "Child Page",
                "markdown": "# Child content",
                "parent_id": "123456",
            },
        )

        assert response.status_code == 200
        call_args = mock_confluence_service.create_or_update_page.call_args
        assert call_args[1]["parent_id"] == "123456"

    def test_convert_from_markdown_missing_fields(self, client: TestClient) -> None:
        """Test conversion without required fields."""
        response = client.post(
            "/confluence/convert-from-markdown",
            json={"space_key": "TEST"},
        )

        assert response.status_code == 422  # Validation error

    def test_convert_from_markdown_service_error(
        self, client: TestClient, mock_confluence_service: MagicMock
    ) -> None:
        """Test conversion with Confluence error."""
        mock_confluence_service.create_or_update_page.side_effect = ConfluenceError(
            "Failed to create page", {}
        )

        response = client.post(
            "/confluence/convert-from-markdown",
            json={
                "space_key": "TEST",
                "title": "New Page",
                "markdown": "# Content",
            },
        )

        assert response.status_code == 500


@pytest.mark.unit
class TestSummarizePageEndpoint:
    """Test cases for POST /confluence/summarize endpoint."""

    def test_summarize_page_success(
        self, client: TestClient, mock_confluence_service: MagicMock, mock_ollama_service: MagicMock
    ) -> None:
        """Test successful page summarization."""
        response = client.post(
            "/confluence/summarize",
            json={"page_id": "123456", "model": "mistral:latest"},
        )

        assert response.status_code == 200
        result = response.json()
        assert result["summary"] == "This is a summary of the page content."
        assert result["page_title"] == "Test Page"
        mock_confluence_service.get_page_by_id.assert_called_once_with("123456")
        mock_ollama_service.generate_text.assert_called_once()

    def test_summarize_page_default_model(
        self, client: TestClient, mock_ollama_service: MagicMock
    ) -> None:
        """Test summarization with default model."""
        response = client.post(
            "/confluence/summarize",
            json={"page_id": "123456"},
        )

        assert response.status_code == 200
        # Should use default model (mistral:latest)
        call_args = mock_ollama_service.generate_text.call_args
        assert "mistral" in call_args[1]["model"].lower()

    def test_summarize_page_missing_page_id(self, client: TestClient) -> None:
        """Test summarization without page_id."""
        response = client.post(
            "/confluence/summarize",
            json={},
        )

        assert response.status_code == 422  # Validation error

    def test_summarize_page_not_found(
        self, client: TestClient, mock_confluence_service: MagicMock
    ) -> None:
        """Test summarization with non-existent page."""
        mock_confluence_service.get_page_by_id.side_effect = ResourceNotFoundError(
            "Page not found", {}
        )

        response = client.post(
            "/confluence/summarize",
            json={"page_id": "999999"},
        )

        assert response.status_code == 404


@pytest.mark.unit
class TestBackupSpaceEndpoint:
    """Test cases for POST /confluence/backup-space endpoint."""

    def test_backup_space_success(
        self,
        client: TestClient,
        mock_confluence_service: MagicMock,
        mock_storage_service: MagicMock,
    ) -> None:
        """Test successful space backup."""
        response = client.post(
            "/confluence/backup-space",
            json={"space_key": "TEST", "format": "html"},
        )

        assert response.status_code == 200
        result = response.json()
        assert result["bucket"] == "confluence-backups"
        assert "TEST" in result["path"]
        assert result["page_count"] == 2
        mock_confluence_service.backup_space.assert_called_once_with("TEST")
        # Should have called upload_file for each page
        assert mock_storage_service.upload_file.call_count == 2

    def test_backup_space_missing_space_key(self, client: TestClient) -> None:
        """Test backup without space_key."""
        response = client.post(
            "/confluence/backup-space",
            json={"format": "html"},
        )

        assert response.status_code == 422  # Validation error

    def test_backup_space_invalid_format(self, client: TestClient) -> None:
        """Test backup with invalid format."""
        response = client.post(
            "/confluence/backup-space",
            json={"space_key": "TEST", "format": "invalid"},
        )

        assert response.status_code == 422  # Validation error

    def test_backup_space_empty(
        self,
        client: TestClient,
        mock_confluence_service: MagicMock,
        mock_storage_service: MagicMock,
    ) -> None:
        """Test backup of empty space."""
        mock_confluence_service.backup_space.return_value = []

        response = client.post(
            "/confluence/backup-space",
            json={"space_key": "EMPTY", "format": "html"},
        )

        assert response.status_code == 200
        result = response.json()
        assert result["page_count"] == 0
        mock_storage_service.upload_file.assert_not_called()

    def test_backup_space_service_error(
        self, client: TestClient, mock_confluence_service: MagicMock
    ) -> None:
        """Test backup with Confluence error."""
        mock_confluence_service.backup_space.side_effect = ConfluenceError(
            "Failed to backup space", {}
        )

        response = client.post(
            "/confluence/backup-space",
            json={"space_key": "TEST", "format": "html"},
        )

        assert response.status_code == 500


@pytest.mark.unit
class TestStatisticsEndpoint:
    """Test cases for POST /confluence/statistics endpoint."""

    def test_get_statistics_success(
        self, client: TestClient, mock_confluence_service: MagicMock
    ) -> None:
        """Test successful statistics retrieval."""
        response = client.post(
            "/confluence/statistics",
            json={"space_key": "TEST"},
        )

        assert response.status_code == 200
        result = response.json()
        assert result["space_key"] == "TEST"
        assert result["space_name"] == "Test Space"
        assert result["total_pages"] == 10
        assert result["total_size_bytes"] == 5000
        assert len(result["contributors"]) == 2
        assert result["last_updated"] == "2025-01-15T10:00:00.000Z"
        mock_confluence_service.get_space_statistics.assert_called_once_with("TEST")

    def test_get_statistics_missing_space_key(self, client: TestClient) -> None:
        """Test statistics without space_key."""
        response = client.post(
            "/confluence/statistics",
            json={},
        )

        assert response.status_code == 422  # Validation error

    def test_get_statistics_service_error(
        self, client: TestClient, mock_confluence_service: MagicMock
    ) -> None:
        """Test statistics with Confluence error."""
        mock_confluence_service.get_space_statistics.side_effect = ConfluenceError(
            "Failed to get statistics", {}
        )

        response = client.post(
            "/confluence/statistics",
            json={"space_key": "TEST"},
        )

        assert response.status_code == 500


@pytest.mark.unit
class TestGetModelsEndpoint:
    """Test cases for GET /confluence/models endpoint."""

    def test_get_models_success(self, client: TestClient, mock_ollama_service: MagicMock) -> None:
        """Test successful model list retrieval."""
        response = client.get("/confluence/models")

        assert response.status_code == 200
        result = response.json()
        assert len(result["models"]) == 2
        assert result["models"][0]["name"] == "mistral:latest"
        assert result["models"][1]["name"] == "llama3.2:latest"
        mock_ollama_service.list_models.assert_called_once()

    def test_get_models_service_error(
        self, client: TestClient, mock_ollama_service: MagicMock
    ) -> None:
        """Test model list with Ollama error."""
        mock_ollama_service.list_models.side_effect = ServiceUnavailableError("Ollama unreachable")

        response = client.get("/confluence/models")

        assert response.status_code == 503
