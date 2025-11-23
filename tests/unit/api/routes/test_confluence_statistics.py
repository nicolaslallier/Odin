"""Unit tests for Confluence statistics API endpoint.

This module tests the statistics endpoint following TDD principles,
ensuring proper integration with Vault, ConfluenceService, and error handling.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException

from src.api.exceptions import ConfluenceError, ResourceNotFoundError, ServiceUnavailableError


@pytest.mark.unit
class TestConfluenceStatisticsEndpoint:
    """Unit tests for POST /confluence/statistics endpoint."""

    @pytest.fixture
    def mock_vault_service(self):
        """Mock VaultService for credential retrieval."""
        mock = MagicMock()
        mock.read_secret.return_value = {
            "base_url": "https://test.atlassian.net/wiki",
            "email": "test@example.com",
            "api_token": "test-token-123",
        }
        return mock

    @pytest.fixture
    def mock_confluence_service(self):
        """Mock ConfluenceService for Confluence API interactions."""
        mock = AsyncMock()
        mock.get_space_statistics.return_value = {
            "space_key": "TEST",
            "space_name": "Test Space",
            "total_pages": 42,
            "total_size_bytes": 1024000,
            "contributors": ["user1@example.com", "user2@example.com"],
            "last_updated": "2025-11-23T10:00:00.000Z",
        }
        mock.close = AsyncMock()
        return mock

    async def test_get_statistics_success(
        self, mock_vault_service, mock_confluence_service
    ):
        """Test successful retrieval of space statistics.

        Given: A valid space key
        When: The statistics endpoint is called
        Then: Statistics are retrieved from Confluence and returned
        """
        with patch(
            "src.api.routes.confluence._get_confluence_service"
        ) as mock_get_service:
            mock_get_service.return_value = mock_confluence_service

            from src.api.routes.confluence import get_statistics, StatisticsRequest

            payload = StatisticsRequest(space_key="TEST")
            result = await get_statistics(payload, mock_vault_service)

            # Verify Confluence service was called with correct space key
            mock_confluence_service.get_space_statistics.assert_called_once_with("TEST")

            # Verify service was properly closed
            mock_confluence_service.close.assert_called_once()

            # Verify correct statistics returned
            assert result["space_key"] == "TEST"
            assert result["space_name"] == "Test Space"
            assert result["total_pages"] == 42
            assert result["total_size_bytes"] == 1024000
            assert len(result["contributors"]) == 2

    async def test_get_statistics_empty_space(
        self, mock_vault_service, mock_confluence_service
    ):
        """Test statistics for an empty space.

        Given: A space with no pages
        When: The statistics endpoint is called
        Then: Returns zero pages but valid space info
        """
        mock_confluence_service.get_space_statistics.return_value = {
            "space_key": "EMPTY",
            "space_name": "Empty Space",
            "total_pages": 0,
            "total_size_bytes": 0,
            "contributors": [],
            "last_updated": None,
        }

        with patch(
            "src.api.routes.confluence._get_confluence_service"
        ) as mock_get_service:
            mock_get_service.return_value = mock_confluence_service

            from src.api.routes.confluence import get_statistics, StatisticsRequest

            payload = StatisticsRequest(space_key="EMPTY")
            result = await get_statistics(payload, mock_vault_service)

            assert result["total_pages"] == 0
            assert result["total_size_bytes"] == 0
            assert result["contributors"] == []

    async def test_get_statistics_large_space(
        self, mock_vault_service, mock_confluence_service
    ):
        """Test statistics for a large space with many pages.

        Given: A space with 10,000+ pages
        When: The statistics endpoint is called
        Then: Returns accurate large numbers
        """
        mock_confluence_service.get_space_statistics.return_value = {
            "space_key": "LARGE",
            "space_name": "Large Space",
            "total_pages": 10543,
            "total_size_bytes": 524288000,  # 500MB
            "contributors": [f"user{i}@example.com" for i in range(50)],
            "last_updated": "2025-11-23T10:00:00.000Z",
        }

        with patch(
            "src.api.routes.confluence._get_confluence_service"
        ) as mock_get_service:
            mock_get_service.return_value = mock_confluence_service

            from src.api.routes.confluence import get_statistics, StatisticsRequest

            payload = StatisticsRequest(space_key="LARGE")
            result = await get_statistics(payload, mock_vault_service)

            assert result["total_pages"] == 10543
            assert result["total_size_bytes"] == 524288000
            assert len(result["contributors"]) == 50

    async def test_get_statistics_space_not_found(
        self, mock_vault_service, mock_confluence_service
    ):
        """Test statistics for non-existent space.

        Given: An invalid/non-existent space key
        When: The statistics endpoint is called
        Then: Returns 404 error
        """
        mock_confluence_service.get_space_statistics.side_effect = ResourceNotFoundError(
            "Space 'NOTFOUND' does not exist"
        )

        with patch(
            "src.api.routes.confluence._get_confluence_service"
        ) as mock_get_service:
            mock_get_service.return_value = mock_confluence_service

            from src.api.routes.confluence import get_statistics, StatisticsRequest

            payload = StatisticsRequest(space_key="NOTFOUND")

            with pytest.raises(HTTPException) as exc_info:
                await get_statistics(payload, mock_vault_service)

            assert exc_info.value.status_code == 404

    async def test_get_statistics_no_vault_credentials(self, mock_vault_service):
        """Test statistics when Vault credentials are missing.

        Given: Vault does not contain Confluence credentials
        When: The statistics endpoint is called
        Then: Returns 404 error about missing credentials
        """
        with patch(
            "src.api.routes.confluence._get_confluence_service"
        ) as mock_get_service:
            # _get_confluence_service raises HTTPException directly
            mock_get_service.side_effect = HTTPException(
                status_code=404, detail="Confluence credentials not found in Vault"
            )

            from src.api.routes.confluence import get_statistics, StatisticsRequest

            payload = StatisticsRequest(space_key="TEST")

            with pytest.raises(HTTPException) as exc_info:
                await get_statistics(payload, mock_vault_service)

            # HTTPException is re-raised as-is (line 488-490 in implementation)
            assert exc_info.value.status_code == 404
            assert "credentials" in exc_info.value.detail.lower()

    async def test_get_statistics_confluence_api_error(
        self, mock_vault_service, mock_confluence_service
    ):
        """Test statistics when Confluence API returns error.

        Given: Confluence API is returning errors
        When: The statistics endpoint is called
        Then: Returns 500 error with details
        """
        mock_confluence_service.get_space_statistics.side_effect = ConfluenceError(
            "Confluence API error: Rate limit exceeded"
        )

        with patch(
            "src.api.routes.confluence._get_confluence_service"
        ) as mock_get_service:
            mock_get_service.return_value = mock_confluence_service

            from src.api.routes.confluence import get_statistics, StatisticsRequest

            payload = StatisticsRequest(space_key="TEST")

            with pytest.raises(HTTPException) as exc_info:
                await get_statistics(payload, mock_vault_service)

            assert exc_info.value.status_code == 500

    async def test_get_statistics_service_unavailable(
        self, mock_vault_service, mock_confluence_service
    ):
        """Test statistics when Confluence service is unavailable.

        Given: Confluence Cloud is unreachable
        When: The statistics endpoint is called
        Then: Returns 503 service unavailable error
        """
        mock_confluence_service.get_space_statistics.side_effect = (
            ServiceUnavailableError("Cannot connect to Confluence Cloud")
        )

        with patch(
            "src.api.routes.confluence._get_confluence_service"
        ) as mock_get_service:
            mock_get_service.return_value = mock_confluence_service

            from src.api.routes.confluence import get_statistics, StatisticsRequest

            payload = StatisticsRequest(space_key="TEST")

            with pytest.raises(HTTPException) as exc_info:
                await get_statistics(payload, mock_vault_service)

            assert exc_info.value.status_code == 503

    async def test_get_statistics_invalid_credentials(self, mock_vault_service):
        """Test statistics with invalid Confluence credentials.

        Given: Confluence credentials are invalid/expired
        When: The statistics endpoint is called
        Then: Returns 503 error about authentication failure
        """
        with patch(
            "src.api.routes.confluence._get_confluence_service"
        ) as mock_get_service:
            # _get_confluence_service raises HTTPException directly
            mock_get_service.side_effect = HTTPException(
                status_code=503,
                detail="Failed to initialize Confluence service: Authentication failed",
            )

            from src.api.routes.confluence import get_statistics, StatisticsRequest

            payload = StatisticsRequest(space_key="TEST")

            with pytest.raises(HTTPException) as exc_info:
                await get_statistics(payload, mock_vault_service)

            # HTTPException is re-raised as-is (line 488-490 in implementation)
            assert exc_info.value.status_code == 503
            assert "Confluence service" in exc_info.value.detail

    async def test_get_statistics_ensures_service_cleanup(
        self, mock_vault_service, mock_confluence_service
    ):
        """Test that Confluence service is properly closed even on error.

        Given: An error occurs during statistics retrieval
        When: The statistics endpoint is called
        Then: Service close() is called in cleanup (finally block)
        """
        mock_confluence_service.get_space_statistics.side_effect = ConfluenceError(
            "Unexpected error"
        )

        with patch(
            "src.api.routes.confluence._get_confluence_service"
        ) as mock_get_service:
            mock_get_service.return_value = mock_confluence_service

            from src.api.routes.confluence import get_statistics, StatisticsRequest

            payload = StatisticsRequest(space_key="TEST")

            with pytest.raises(HTTPException):
                await get_statistics(payload, mock_vault_service)

            # Verify service was closed despite error (finally block ensures this)
            mock_confluence_service.close.assert_called_once()


@pytest.mark.regression
class TestConfluenceStatisticsRegression:
    """Regression tests for previously fixed statistics bugs."""

    @pytest.fixture
    def mock_vault_service(self):
        """Mock VaultService for credential retrieval."""
        mock = MagicMock()
        mock.read_secret.return_value = {
            "base_url": "https://test.atlassian.net/wiki",
            "email": "test@example.com",
            "api_token": "test-token-123",
        }
        return mock

    @pytest.fixture
    def mock_confluence_service(self):
        """Mock ConfluenceService for Confluence API interactions."""
        mock = AsyncMock()
        mock.close = AsyncMock()
        return mock

    async def test_regression_vault_credentials_missing_returns_404(
        self, mock_vault_service
    ):
        """Regression test: Ensure missing Vault credentials return 404, not 500.

        Bug: Previously returned 500 when credentials were missing from Vault
        Fix: Now correctly returns 404 with clear error message
        Date: 2025-11-23

        Given: Vault does not contain Confluence credentials
        When: Statistics endpoint is called
        Then: Returns 404 (not 500) with helpful error message
        """
        with patch(
            "src.api.routes.confluence._get_confluence_service"
        ) as mock_get_service:
            # _get_confluence_service raises HTTPException(404)
            mock_get_service.side_effect = HTTPException(
                status_code=404,
                detail="Confluence credentials not found in Vault at path: confluence/credentials",
            )

            from src.api.routes.confluence import get_statistics, StatisticsRequest

            payload = StatisticsRequest(space_key="TEST")

            with pytest.raises(HTTPException) as exc_info:
                await get_statistics(payload, mock_vault_service)

            # Verify correct status code (404, not 500) - HTTPException re-raised as-is
            assert exc_info.value.status_code == 404
            # Verify helpful error message
            assert "credentials" in exc_info.value.detail.lower()
            assert "vault" in exc_info.value.detail.lower()

    async def test_regression_statistics_response_includes_all_fields(
        self, mock_vault_service, mock_confluence_service
    ):
        """Regression test: Ensure all statistics fields are returned.

        Bug: Some fields were occasionally missing from response
        Fix: Validate complete response structure
        Date: 2025-11-23

        Given: A valid space with statistics
        When: Statistics are retrieved
        Then: All expected fields are present in response
        """
        mock_confluence_service.get_space_statistics.return_value = {
            "space_key": "TEST",
            "space_name": "Test Space",
            "total_pages": 42,
            "total_size_bytes": 1024000,
            "contributors": ["user@example.com"],
            "last_updated": "2025-11-23T10:00:00.000Z",
        }

        with patch(
            "src.api.routes.confluence._get_confluence_service"
        ) as mock_get_service:
            mock_get_service.return_value = mock_confluence_service

            from src.api.routes.confluence import get_statistics, StatisticsRequest

            payload = StatisticsRequest(space_key="TEST")
            result = await get_statistics(payload, mock_vault_service)

            # Verify all required fields are present
            required_fields = [
                "space_key",
                "space_name",
                "total_pages",
                "total_size_bytes",
                "contributors",
                "last_updated",
            ]
            for field in required_fields:
                assert field in result, f"Missing required field: {field}"

    async def test_regression_service_cleanup_on_error(
        self, mock_vault_service, mock_confluence_service
    ):
        """Regression test: Ensure service cleanup happens on error.

        Bug: ConfluenceService.close() was not called when errors occurred
        Fix: Use try/finally to ensure cleanup (lines 499-501 in implementation)
        Date: 2025-11-23

        Given: An error occurs during statistics retrieval
        When: The endpoint is called
        Then: Service close() is still called for cleanup via finally block
        """
        mock_confluence_service.get_space_statistics.side_effect = ConfluenceError(
            "API error"
        )

        with patch(
            "src.api.routes.confluence._get_confluence_service"
        ) as mock_get_service:
            mock_get_service.return_value = mock_confluence_service

            from src.api.routes.confluence import get_statistics, StatisticsRequest

            payload = StatisticsRequest(space_key="TEST")

            with pytest.raises(HTTPException):
                await get_statistics(payload, mock_vault_service)

            # Verify cleanup happened via finally block
            mock_confluence_service.close.assert_called_once()

    async def test_regression_unicode_space_names_handled(
        self, mock_vault_service, mock_confluence_service
    ):
        """Regression test: Handle Unicode characters in space names.

        Bug: Unicode characters in space names caused encoding errors
        Fix: Proper UTF-8 handling throughout
        Date: 2025-11-23

        Given: A space with Unicode characters in name
        When: Statistics are retrieved
        Then: Unicode characters are preserved correctly
        """
        mock_confluence_service.get_space_statistics.return_value = {
            "space_key": "INTL",
            "space_name": "国际化 Space with émojis 🚀",
            "total_pages": 10,
            "total_size_bytes": 50000,
            "contributors": ["user@例え.com", "用户@example.com"],
            "last_updated": "2025-11-23T10:00:00.000Z",
        }

        with patch(
            "src.api.routes.confluence._get_confluence_service"
        ) as mock_get_service:
            mock_get_service.return_value = mock_confluence_service

            from src.api.routes.confluence import get_statistics, StatisticsRequest

            payload = StatisticsRequest(space_key="INTL")
            result = await get_statistics(payload, mock_vault_service)

            # Verify Unicode preserved
            assert "国际化" in result["space_name"]
            assert "🚀" in result["space_name"]
            assert "例え" in result["contributors"][0]
            assert "用户" in result["contributors"][1]

