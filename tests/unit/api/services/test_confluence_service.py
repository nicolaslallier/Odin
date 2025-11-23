"""Unit tests for ConfluenceService.

This module tests the Confluence API client service with comprehensive coverage
of all operations: page retrieval, conversion, backup, and statistics.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, Mock

import httpx
import pytest

from src.api.exceptions import (
    ResourceNotFoundError,
    ServiceUnavailableError,
)
from src.api.services.confluence import ConfluenceService


@pytest.fixture
def confluence_service() -> ConfluenceService:
    """Create a ConfluenceService instance for testing.

    Returns:
        ConfluenceService instance with test credentials
    """
    service = ConfluenceService(
        base_url="https://test.atlassian.net/wiki",
        email="test@example.com",
        api_token="test-token-123",
    )
    return service


@pytest.fixture
def mock_client() -> Mock:
    """Create a mock httpx.AsyncClient for testing.

    Returns:
        Mock HTTP client
    """
    client = Mock(spec=httpx.AsyncClient)
    return client


@pytest.mark.unit
class TestConfluenceServiceInit:
    """Test cases for ConfluenceService initialization."""

    def test_initialization(self) -> None:
        """Test that ConfluenceService initializes with correct parameters."""
        service = ConfluenceService(
            base_url="https://test.atlassian.net/wiki",
            email="test@example.com",
            api_token="test-token",
        )

        assert service.base_url == "https://test.atlassian.net/wiki"
        assert service.email == "test@example.com"
        assert service.api_token == "test-token"
        assert service._client is None

    @pytest.mark.asyncio
    async def test_initialize_client(self, confluence_service: ConfluenceService) -> None:
        """Test that initialize creates HTTP client."""
        await confluence_service.initialize()
        assert confluence_service._client is not None
        assert isinstance(confluence_service._client, httpx.AsyncClient)
        await confluence_service.close()

    @pytest.mark.asyncio
    async def test_close_client(self, confluence_service: ConfluenceService) -> None:
        """Test that close properly closes HTTP client."""
        await confluence_service.initialize()
        assert confluence_service._client is not None
        await confluence_service.close()
        assert confluence_service._client is None


@pytest.mark.unit
class TestGetPageById:
    """Test cases for get_page_by_id method."""

    @pytest.mark.asyncio
    async def test_get_page_by_id_success(
        self, confluence_service: ConfluenceService, mock_client: Mock
    ) -> None:
        """Test successful page retrieval."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "id": "123456",
            "type": "page",
            "title": "Test Page",
            "body": {
                "storage": {
                    "value": "<p>Test content</p>",
                    "representation": "storage",
                }
            },
            "space": {"key": "TEST"},
            "version": {"number": 1},
        }
        mock_response.raise_for_status = Mock()

        mock_client.get = AsyncMock(return_value=mock_response)
        confluence_service._client = mock_client

        result = await confluence_service.get_page_by_id("123456")

        assert result["id"] == "123456"
        assert result["title"] == "Test Page"
        assert result["body"]["storage"]["value"] == "<p>Test content</p>"
        mock_client.get.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_page_by_id_not_found(
        self, confluence_service: ConfluenceService, mock_client: Mock
    ) -> None:
        """Test page not found returns ResourceNotFoundError."""
        mock_response = Mock()
        mock_response.status_code = 404
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Not Found", request=Mock(), response=mock_response
        )

        mock_client.get = AsyncMock(return_value=mock_response)
        confluence_service._client = mock_client

        with pytest.raises(ResourceNotFoundError, match="Page not found"):
            await confluence_service.get_page_by_id("999999")

    @pytest.mark.asyncio
    async def test_get_page_by_id_service_error(
        self, confluence_service: ConfluenceService, mock_client: Mock
    ) -> None:
        """Test service error raises ServiceUnavailableError."""
        mock_client.get = AsyncMock(
            side_effect=httpx.RequestError("Connection failed", request=Mock())
        )
        confluence_service._client = mock_client

        with pytest.raises(ServiceUnavailableError, match="Confluence service unreachable"):
            await confluence_service.get_page_by_id("123456")

    @pytest.mark.asyncio
    async def test_get_page_by_id_not_initialized(
        self, confluence_service: ConfluenceService
    ) -> None:
        """Test getting page without initializing client raises error."""
        with pytest.raises(ServiceUnavailableError, match="not initialized"):
            await confluence_service.get_page_by_id("123456")


@pytest.mark.unit
class TestConvertPageToMarkdown:
    """Test cases for convert_page_to_markdown method."""

    @pytest.mark.asyncio
    async def test_convert_page_to_markdown_success(
        self, confluence_service: ConfluenceService, mock_client: Mock
    ) -> None:
        """Test successful HTML to Markdown conversion."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "id": "123456",
            "title": "Test Page",
            "body": {
                "storage": {
                    "value": "<h1>Heading</h1><p>Paragraph text</p><ul><li>Item 1</li></ul>",
                }
            },
        }
        mock_response.raise_for_status = Mock()

        mock_client.get = AsyncMock(return_value=mock_response)
        confluence_service._client = mock_client

        markdown = await confluence_service.convert_page_to_markdown("123456")

        assert "# Heading" in markdown or "Heading" in markdown
        assert "Paragraph text" in markdown
        assert "Item 1" in markdown

    @pytest.mark.asyncio
    async def test_convert_page_to_markdown_empty_content(
        self, confluence_service: ConfluenceService, mock_client: Mock
    ) -> None:
        """Test conversion with empty content."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "id": "123456",
            "title": "Empty Page",
            "body": {"storage": {"value": ""}},
        }
        mock_response.raise_for_status = Mock()

        mock_client.get = AsyncMock(return_value=mock_response)
        confluence_service._client = mock_client

        markdown = await confluence_service.convert_page_to_markdown("123456")

        assert markdown == ""


@pytest.mark.unit
class TestConvertMarkdownToStorage:
    """Test cases for convert_markdown_to_storage method."""

    def test_convert_markdown_to_storage_basic(self, confluence_service: ConfluenceService) -> None:
        """Test basic Markdown to Confluence storage format conversion."""
        markdown = "# Heading\n\nParagraph text\n\n- Item 1\n- Item 2"

        html = confluence_service.convert_markdown_to_storage(markdown)

        assert "<h1>" in html or "<h2>" in html  # Markdown parsers may vary
        assert "Paragraph text" in html
        assert "<li>" in html
        assert "Item 1" in html

    def test_convert_markdown_to_storage_empty(self, confluence_service: ConfluenceService) -> None:
        """Test conversion of empty Markdown."""
        html = confluence_service.convert_markdown_to_storage("")
        assert html == ""

    def test_convert_markdown_to_storage_code_blocks(
        self, confluence_service: ConfluenceService
    ) -> None:
        """Test conversion preserves code blocks."""
        markdown = "```python\nprint('hello')\n```"

        html = confluence_service.convert_markdown_to_storage(markdown)

        assert "print" in html
        assert "hello" in html


@pytest.mark.unit
class TestCreateOrUpdatePage:
    """Test cases for create_or_update_page method."""

    @pytest.mark.asyncio
    async def test_create_page_success(
        self, confluence_service: ConfluenceService, mock_client: Mock
    ) -> None:
        """Test successful page creation."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "id": "789012",
            "type": "page",
            "title": "New Page",
            "_links": {"webui": "/spaces/TEST/pages/789012/New+Page"},
        }
        mock_response.raise_for_status = Mock()

        # Mock GET to check if page exists (returns 404 - doesn't exist)
        mock_get_response = Mock()
        mock_get_response.status_code = 404
        mock_get_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Not Found", request=Mock(), response=mock_get_response
        )

        mock_client.get = AsyncMock(return_value=mock_get_response)
        mock_client.post = AsyncMock(return_value=mock_response)
        confluence_service._client = mock_client

        result = await confluence_service.create_or_update_page(
            space_key="TEST",
            title="New Page",
            content_html="<p>Test content</p>",
            parent_id=None,
        )

        assert result["id"] == "789012"
        assert result["title"] == "New Page"
        mock_client.post.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_page_success(
        self, confluence_service: ConfluenceService, mock_client: Mock
    ) -> None:
        """Test successful page update."""
        # Mock GET to find existing page
        mock_get_response = Mock()
        mock_get_response.status_code = 200
        mock_get_response.json.return_value = {
            "results": [
                {
                    "id": "789012",
                    "version": {"number": 1},
                }
            ]
        }
        mock_get_response.raise_for_status = Mock()

        # Mock PUT to update page
        mock_put_response = Mock()
        mock_put_response.status_code = 200
        mock_put_response.json.return_value = {
            "id": "789012",
            "title": "Updated Page",
            "version": {"number": 2},
        }
        mock_put_response.raise_for_status = Mock()

        mock_client.get = AsyncMock(return_value=mock_get_response)
        mock_client.put = AsyncMock(return_value=mock_put_response)
        confluence_service._client = mock_client

        result = await confluence_service.create_or_update_page(
            space_key="TEST",
            title="Updated Page",
            content_html="<p>Updated content</p>",
            parent_id=None,
        )

        assert result["id"] == "789012"
        assert result["version"]["number"] == 2
        mock_client.put.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_page_with_parent(
        self, confluence_service: ConfluenceService, mock_client: Mock
    ) -> None:
        """Test page creation with parent page."""
        mock_get_response = Mock()
        mock_get_response.status_code = 404
        mock_get_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Not Found", request=Mock(), response=mock_get_response
        )

        mock_post_response = Mock()
        mock_post_response.status_code = 200
        mock_post_response.json.return_value = {
            "id": "789012",
            "title": "Child Page",
        }
        mock_post_response.raise_for_status = Mock()

        mock_client.get = AsyncMock(return_value=mock_get_response)
        mock_client.post = AsyncMock(return_value=mock_post_response)
        confluence_service._client = mock_client

        result = await confluence_service.create_or_update_page(
            space_key="TEST",
            title="Child Page",
            content_html="<p>Child content</p>",
            parent_id="123456",
        )

        assert result["id"] == "789012"
        # Verify parent_id was included in the request
        call_args = mock_client.post.call_args
        assert "ancestors" in call_args[1]["json"]


@pytest.mark.unit
class TestBackupSpace:
    """Test cases for backup_space method."""

    @pytest.mark.asyncio
    async def test_backup_space_success(
        self, confluence_service: ConfluenceService, mock_client: Mock
    ) -> None:
        """Test successful space backup."""
        # Mock response for listing pages
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "results": [
                {
                    "id": "111",
                    "title": "Page 1",
                    "body": {"storage": {"value": "<p>Content 1</p>"}},
                },
                {
                    "id": "222",
                    "title": "Page 2",
                    "body": {"storage": {"value": "<p>Content 2</p>"}},
                },
            ],
            "size": 2,
            "_links": {},  # No next page
        }
        mock_response.raise_for_status = Mock()

        mock_client.get = AsyncMock(return_value=mock_response)
        confluence_service._client = mock_client

        pages = await confluence_service.backup_space("TEST")

        assert len(pages) == 2
        assert pages[0]["id"] == "111"
        assert pages[1]["id"] == "222"
        assert pages[0]["title"] == "Page 1"

    @pytest.mark.asyncio
    async def test_backup_space_pagination(
        self, confluence_service: ConfluenceService, mock_client: Mock
    ) -> None:
        """Test space backup handles pagination."""
        # First page
        mock_response1 = Mock()
        mock_response1.status_code = 200
        mock_response1.json.return_value = {
            "results": [
                {"id": "111", "title": "Page 1", "body": {"storage": {"value": "<p>Content 1</p>"}}}
            ],
            "size": 1,
            "_links": {"next": "/rest/api/content?space=TEST&start=1"},
        }
        mock_response1.raise_for_status = Mock()

        # Second page
        mock_response2 = Mock()
        mock_response2.status_code = 200
        mock_response2.json.return_value = {
            "results": [
                {"id": "222", "title": "Page 2", "body": {"storage": {"value": "<p>Content 2</p>"}}}
            ],
            "size": 1,
            "_links": {},  # No next page
        }
        mock_response2.raise_for_status = Mock()

        mock_client.get = AsyncMock(side_effect=[mock_response1, mock_response2])
        confluence_service._client = mock_client

        pages = await confluence_service.backup_space("TEST")

        assert len(pages) == 2
        assert mock_client.get.call_count == 2

    @pytest.mark.asyncio
    async def test_backup_space_empty(
        self, confluence_service: ConfluenceService, mock_client: Mock
    ) -> None:
        """Test backup of empty space."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"results": [], "size": 0, "_links": {}}
        mock_response.raise_for_status = Mock()

        mock_client.get = AsyncMock(return_value=mock_response)
        confluence_service._client = mock_client

        pages = await confluence_service.backup_space("EMPTY")

        assert len(pages) == 0


@pytest.mark.unit
class TestGetSpaceStatistics:
    """Test cases for get_space_statistics method."""

    @pytest.mark.asyncio
    async def test_get_space_statistics_success(
        self, confluence_service: ConfluenceService, mock_client: Mock
    ) -> None:
        """Test successful statistics retrieval."""
        # Mock space info
        mock_space_response = Mock()
        mock_space_response.status_code = 200
        mock_space_response.json.return_value = {
            "key": "TEST",
            "name": "Test Space",
        }
        mock_space_response.raise_for_status = Mock()

        # Mock pages list
        mock_pages_response = Mock()
        mock_pages_response.status_code = 200
        mock_pages_response.json.return_value = {
            "results": [
                {
                    "id": "111",
                    "title": "Page 1",
                    "version": {
                        "when": "2025-01-01T10:00:00.000Z",
                        "by": {"displayName": "User 1"},
                    },
                    "body": {
                        "storage": {"value": "<p>Content with 50 chars approximately here.</p>"}
                    },
                },
                {
                    "id": "222",
                    "title": "Page 2",
                    "version": {
                        "when": "2025-01-02T10:00:00.000Z",
                        "by": {"displayName": "User 2"},
                    },
                    "body": {"storage": {"value": "<p>More content here.</p>"}},
                },
            ],
            "size": 2,
            "_links": {},
        }
        mock_pages_response.raise_for_status = Mock()

        mock_client.get = AsyncMock(side_effect=[mock_space_response, mock_pages_response])
        confluence_service._client = mock_client

        stats = await confluence_service.get_space_statistics("TEST")

        assert stats["space_key"] == "TEST"
        assert stats["space_name"] == "Test Space"
        assert stats["total_pages"] == 2
        assert stats["total_size_bytes"] > 0
        assert len(stats["contributors"]) == 2
        assert "User 1" in stats["contributors"]
        assert "User 2" in stats["contributors"]
        assert stats["last_updated"] == "2025-01-02T10:00:00.000Z"

    @pytest.mark.asyncio
    async def test_get_space_statistics_empty_space(
        self, confluence_service: ConfluenceService, mock_client: Mock
    ) -> None:
        """Test statistics for empty space."""
        mock_space_response = Mock()
        mock_space_response.status_code = 200
        mock_space_response.json.return_value = {
            "key": "EMPTY",
            "name": "Empty Space",
        }
        mock_space_response.raise_for_status = Mock()

        mock_pages_response = Mock()
        mock_pages_response.status_code = 200
        mock_pages_response.json.return_value = {"results": [], "size": 0, "_links": {}}
        mock_pages_response.raise_for_status = Mock()

        mock_client.get = AsyncMock(side_effect=[mock_space_response, mock_pages_response])
        confluence_service._client = mock_client

        stats = await confluence_service.get_space_statistics("EMPTY")

        assert stats["total_pages"] == 0
        assert stats["total_size_bytes"] == 0
        assert len(stats["contributors"]) == 0
        assert stats["last_updated"] is None


@pytest.mark.unit
class TestHealthCheck:
    """Test cases for health_check method."""

    @pytest.mark.asyncio
    async def test_health_check_healthy(
        self, confluence_service: ConfluenceService, mock_client: Mock
    ) -> None:
        """Test health check returns True when service is accessible."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.raise_for_status = Mock()

        mock_client.get = AsyncMock(return_value=mock_response)
        confluence_service._client = mock_client

        result = await confluence_service.health_check()

        assert result is True

    @pytest.mark.asyncio
    async def test_health_check_unhealthy(
        self, confluence_service: ConfluenceService, mock_client: Mock
    ) -> None:
        """Test health check returns False when service is unreachable."""
        mock_client.get = AsyncMock(
            side_effect=httpx.RequestError("Connection failed", request=Mock())
        )
        confluence_service._client = mock_client

        result = await confluence_service.health_check()

        assert result is False

    @pytest.mark.asyncio
    async def test_health_check_not_initialized(
        self, confluence_service: ConfluenceService
    ) -> None:
        """Test health check returns False when client not initialized."""
        result = await confluence_service.health_check()

        assert result is False
