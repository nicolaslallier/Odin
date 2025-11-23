"""Integration tests for Confluence statistics through web portal.

This module tests the complete flow from web portal to API to Confluence,
ensuring proper end-to-end integration.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from fastapi.testclient import TestClient


@pytest.mark.integration
class TestConfluenceStatisticsIntegration:
    """Integration tests for statistics feature through web portal."""

    @pytest.fixture
    def mock_api_response(self):
        """Mock successful API response."""
        return {
            "space_key": "AIARC",
            "space_name": "AI Architecture",
            "total_pages": 100,
            "total_size_bytes": 628775,
            "contributors": ["Nicolas.Lallier"],
            "last_updated": "2025-11-02T13:26:57.022Z",
        }

    @pytest.fixture
    def mock_httpx_client(self, mock_api_response):
        """Mock httpx AsyncClient for API calls."""

        async def mock_post(*args, **kwargs):
            """Mock POST request."""
            mock_response = MagicMock()
            mock_response.is_success = True
            mock_response.json.return_value = mock_api_response
            mock_response.status_code = 200
            return mock_response

        mock_client = MagicMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client.post = AsyncMock(side_effect=mock_post)
        return mock_client

    async def test_statistics_endpoint_calls_api_correctly(
        self, mock_httpx_client, mock_api_response
    ):
        """Test that portal correctly calls API for statistics.

        Given: A request for space statistics
        When: The portal statistics endpoint is called
        Then: Portal makes correct HTTP call to API service
        """
        from src.web.routes.confluence import get_statistics, StatisticsRequest

        # Create mock request with config
        mock_request = MagicMock()
        mock_request.app.state.config.api_base_url = "http://test-api:8001"

        payload = StatisticsRequest(space_key="AIARC")

        with patch("httpx.AsyncClient", return_value=mock_httpx_client):
            result = await get_statistics(mock_request, payload)

            # Verify API was called
            mock_httpx_client.post.assert_called_once()
            call_args = mock_httpx_client.post.call_args

            # Verify correct URL
            assert call_args[0][0] == "http://test-api:8001/confluence/statistics"

            # Verify correct payload
            assert call_args[1]["json"]["space_key"] == "AIARC"

            # Verify response contains expected data
            import json

            result_data = json.loads(result.body)
            assert result_data["space_key"] == "AIARC"
            assert result_data["total_pages"] == 100

    async def test_statistics_endpoint_handles_api_404(self, mock_httpx_client):
        """Test portal handling of API 404 (space not found).

        Given: API returns 404 for non-existent space
        When: Portal statistics endpoint is called
        Then: Portal returns 404 with error details
        """

        async def mock_post_404(*args, **kwargs):
            """Mock POST request returning 404."""
            mock_response = MagicMock()
            mock_response.is_success = False
            mock_response.status_code = 404
            mock_response.json.return_value = {"detail": "Space 'NOTFOUND' does not exist"}
            mock_response.text = "Space 'NOTFOUND' does not exist"
            return mock_response

        mock_httpx_client.post = AsyncMock(side_effect=mock_post_404)

        from fastapi import HTTPException

        from src.web.routes.confluence import get_statistics, StatisticsRequest

        mock_request = MagicMock()
        mock_request.app.state.config.api_base_url = "http://test-api:8001"
        payload = StatisticsRequest(space_key="NOTFOUND")

        with patch("httpx.AsyncClient", return_value=mock_httpx_client):
            with pytest.raises(HTTPException) as exc_info:
                await get_statistics(mock_request, payload)

            assert exc_info.value.status_code == 404

    async def test_statistics_endpoint_handles_api_500(self, mock_httpx_client):
        """Test portal handling of API 500 (internal error).

        Given: API returns 500 internal server error
        When: Portal statistics endpoint is called
        Then: Portal returns 500 with error details
        """

        async def mock_post_500(*args, **kwargs):
            """Mock POST request returning 500."""
            mock_response = MagicMock()
            mock_response.is_success = False
            mock_response.status_code = 500
            mock_response.json.return_value = {
                "detail": "Failed to get statistics: Confluence API error"
            }
            mock_response.text = "Failed to get statistics"
            return mock_response

        mock_httpx_client.post = AsyncMock(side_effect=mock_post_500)

        from fastapi import HTTPException

        from src.web.routes.confluence import get_statistics, StatisticsRequest

        mock_request = MagicMock()
        mock_request.app.state.config.api_base_url = "http://test-api:8001"
        payload = StatisticsRequest(space_key="TEST")

        with patch("httpx.AsyncClient", return_value=mock_httpx_client):
            with pytest.raises(HTTPException) as exc_info:
                await get_statistics(mock_request, payload)

            assert exc_info.value.status_code == 500

    async def test_statistics_endpoint_handles_api_unreachable(self):
        """Test portal handling when API service is unreachable.

        Given: API service is not responding
        When: Portal tries to get statistics
        Then: Portal returns 503 service unavailable
        """

        async def mock_post_error(*args, **kwargs):
            """Mock POST request that fails to connect."""
            raise httpx.ConnectError("Failed to connect to API service")

        mock_client = MagicMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client.post = AsyncMock(side_effect=mock_post_error)

        from fastapi import HTTPException

        from src.web.routes.confluence import get_statistics, StatisticsRequest

        mock_request = MagicMock()
        mock_request.app.state.config.api_base_url = "http://unreachable:8001"
        payload = StatisticsRequest(space_key="TEST")

        with patch("httpx.AsyncClient", return_value=mock_client):
            with pytest.raises(HTTPException) as exc_info:
                await get_statistics(mock_request, payload)

            assert exc_info.value.status_code == 503
            assert "Failed to connect to API service" in exc_info.value.detail

    async def test_statistics_endpoint_timeout_handling(self):
        """Test portal handling of API timeout.

        Given: API takes too long to respond
        When: Portal statistics endpoint is called
        Then: Portal returns appropriate timeout error
        """

        async def mock_post_timeout(*args, **kwargs):
            """Mock POST request that times out."""
            raise httpx.TimeoutException("Request timed out")

        mock_client = MagicMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client.post = AsyncMock(side_effect=mock_post_timeout)

        from fastapi import HTTPException

        from src.web.routes.confluence import get_statistics, StatisticsRequest

        mock_request = MagicMock()
        mock_request.app.state.config.api_base_url = "http://test-api:8001"
        payload = StatisticsRequest(space_key="TEST")

        with patch("httpx.AsyncClient", return_value=mock_client):
            with pytest.raises(HTTPException) as exc_info:
                await get_statistics(mock_request, payload)

            assert exc_info.value.status_code == 503


@pytest.mark.integration
class TestConfluenceStatisticsE2E:
    """End-to-end tests for statistics through full stack."""

    @pytest.fixture
    def mock_confluence_api_response(self):
        """Mock Confluence Cloud API response."""
        return {
            "space_key": "E2E",
            "space_name": "E2E Test Space",
            "total_pages": 25,
            "total_size_bytes": 102400,
            "contributors": ["test@example.com"],
            "last_updated": "2025-11-23T12:00:00.000Z",
        }

    async def test_e2e_statistics_flow_success(self, mock_confluence_api_response):
        """Test complete flow from browser to Confluence and back.

        Flow:
        1. Browser → Web Portal (POST /confluence/statistics)
        2. Web Portal → Odin API (POST /confluence/statistics)
        3. Odin API → Vault (get credentials)
        4. Odin API → Confluence Cloud (get statistics)
        5. Response flows back through layers

        Given: All services are available and configured
        When: User requests space statistics
        Then: Statistics are successfully retrieved and returned
        """
        # Mock Vault response
        mock_vault = MagicMock()
        mock_vault.read_secret.return_value = {
            "base_url": "https://test.atlassian.net/wiki",
            "email": "test@example.com",
            "api_token": "test-token",
        }

        # Mock Confluence service
        mock_confluence = AsyncMock()
        mock_confluence.get_space_statistics.return_value = mock_confluence_api_response
        mock_confluence.close = AsyncMock()

        # Mock httpx for portal→API communication
        async def mock_api_call(*args, **kwargs):
            mock_response = MagicMock()
            mock_response.is_success = True
            mock_response.json.return_value = mock_confluence_api_response
            mock_response.status_code = 200
            return mock_response

        mock_http_client = MagicMock()
        mock_http_client.__aenter__ = AsyncMock(return_value=mock_http_client)
        mock_http_client.__aexit__ = AsyncMock(return_value=None)
        mock_http_client.post = AsyncMock(side_effect=mock_api_call)

        # Execute E2E flow
        from src.web.routes.confluence import get_statistics, StatisticsRequest

        mock_request = MagicMock()
        mock_request.app.state.config.api_base_url = "http://test-api:8001"
        payload = StatisticsRequest(space_key="E2E")

        with patch("httpx.AsyncClient", return_value=mock_http_client):
            result = await get_statistics(mock_request, payload)

            # Verify complete flow executed
            mock_http_client.post.assert_called_once()

            # Verify correct response
            import json

            result_data = json.loads(result.body)
            assert result_data["space_key"] == "E2E"
            assert result_data["space_name"] == "E2E Test Space"
            assert result_data["total_pages"] == 25

    async def test_e2e_statistics_with_large_response(self):
        """Test E2E flow with large statistics response.

        Given: A space with many pages and contributors
        When: Statistics are requested
        Then: Large response is handled correctly
        """
        large_response = {
            "space_key": "LARGE",
            "space_name": "Large Space",
            "total_pages": 5000,
            "total_size_bytes": 104857600,  # 100MB
            "contributors": [f"user{i}@example.com" for i in range(100)],
            "last_updated": "2025-11-23T12:00:00.000Z",
        }

        async def mock_api_call(*args, **kwargs):
            mock_response = MagicMock()
            mock_response.is_success = True
            mock_response.json.return_value = large_response
            mock_response.status_code = 200
            return mock_response

        mock_http_client = MagicMock()
        mock_http_client.__aenter__ = AsyncMock(return_value=mock_http_client)
        mock_http_client.__aexit__ = AsyncMock(return_value=None)
        mock_http_client.post = AsyncMock(side_effect=mock_api_call)

        from src.web.routes.confluence import get_statistics, StatisticsRequest

        mock_request = MagicMock()
        mock_request.app.state.config.api_base_url = "http://test-api:8001"
        payload = StatisticsRequest(space_key="LARGE")

        with patch("httpx.AsyncClient", return_value=mock_http_client):
            result = await get_statistics(mock_request, payload)

            import json

            result_data = json.loads(result.body)
            assert result_data["total_pages"] == 5000
            assert len(result_data["contributors"]) == 100


@pytest.mark.regression
class TestConfluenceStatisticsWebRegression:
    """Regression tests for web portal statistics bugs."""

    async def test_regression_api_base_url_construction(self):
        """Regression test: Ensure API URL is constructed correctly.

        Bug: API URL was being double-prefixed with /api
        Fix: Use api_base_url directly without additional prefix
        Date: 2025-11-23

        Given: Portal config has API base URL
        When: Statistics endpoint constructs API URL
        Then: URL is correct without double-prefix
        """
        mock_client = MagicMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        captured_url = None

        async def capture_url(url, **kwargs):
            nonlocal captured_url
            captured_url = url
            mock_response = MagicMock()
            mock_response.is_success = True
            mock_response.json.return_value = {"space_key": "TEST"}
            return mock_response

        mock_client.post = AsyncMock(side_effect=capture_url)

        from src.web.routes.confluence import get_statistics, StatisticsRequest

        mock_request = MagicMock()
        mock_request.app.state.config.api_base_url = "http://odin-api:8001"
        payload = StatisticsRequest(space_key="TEST")

        with patch("httpx.AsyncClient", return_value=mock_client):
            await get_statistics(mock_request, payload)

            # Verify URL is correct (no double /api prefix)
            assert captured_url == "http://odin-api:8001/confluence/statistics"
            assert "/api/api/" not in captured_url

    async def test_regression_error_detail_extraction(self):
        """Regression test: Properly extract error details from API response.

        Bug: Error messages were showing as [object Object]
        Fix: Correctly extract 'detail' field from JSON response
        Date: 2025-11-23

        Given: API returns error with detail field
        When: Portal receives the error
        Then: Detail is properly extracted and forwarded
        """

        async def mock_api_error(*args, **kwargs):
            mock_response = MagicMock()
            mock_response.is_success = False
            mock_response.status_code = 404
            mock_response.json.return_value = {
                "detail": "Confluence credentials not found in Vault"
            }
            mock_response.text = "Error"
            return mock_response

        mock_client = MagicMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client.post = AsyncMock(side_effect=mock_api_error)

        from fastapi import HTTPException

        from src.web.routes.confluence import get_statistics, StatisticsRequest

        mock_request = MagicMock()
        mock_request.app.state.config.api_base_url = "http://test-api:8001"
        payload = StatisticsRequest(space_key="TEST")

        with patch("httpx.AsyncClient", return_value=mock_client):
            with pytest.raises(HTTPException) as exc_info:
                await get_statistics(mock_request, payload)

            # Verify error detail is properly extracted
            assert "Confluence credentials not found" in exc_info.value.detail
            assert "[object Object]" not in exc_info.value.detail
