"""Unit tests for health record endpoint.

This module tests the /health/record endpoint including correlation ID handling.
"""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.api.models.schemas import HealthCheckBatchRequest, HealthCheckRecord
from src.api.routes.health import router


@pytest.fixture
def app() -> FastAPI:
    """Create FastAPI app with health routes.

    Returns:
        FastAPI application instance
    """
    app = FastAPI()
    app.include_router(router)
    return app


@pytest.fixture
def client(app: FastAPI) -> TestClient:
    """Create test client.

    Args:
        app: FastAPI application

    Returns:
        Test client instance
    """
    return TestClient(app)


class TestHealthRecordEndpoint:
    """Tests for /health/record endpoint."""

    @pytest.mark.asyncio
    async def test_record_health_checks_accepts_correlation_id_header(self) -> None:
        """Test that endpoint accepts X-Correlation-ID header.

        This test verifies the endpoint can receive and process the correlation ID
        from the request header for tracking health check runs.
        """
        # Mock repository
        mock_repository = AsyncMock()
        mock_repository.insert_health_checks.return_value = 2

        # Create request
        request_data = {
            "checks": [
                {
                    "service_name": "database",
                    "service_type": "infrastructure",
                    "is_healthy": True,
                    "response_time_ms": 12.5,
                    "metadata": {},
                },
                {
                    "service_name": "api",
                    "service_type": "application",
                    "is_healthy": True,
                    "response_time_ms": 8.3,
                    "metadata": {},
                },
            ],
        }

        correlation_id = "550e8400-e29b-41d4-a716-446655440000"

        # Import and patch the endpoint
        from src.api.routes.health import record_health_checks

        # Mock the dependency
        async def mock_get_health_repository():
            yield mock_repository

        # Test directly with mocked repository
        request = HealthCheckBatchRequest(**request_data)
        result = await record_health_checks(
            request=request, repository=mock_repository, correlation_id=correlation_id
        )

        # Verify response
        assert result.recorded == 2
        assert result.message == "Health checks recorded successfully"

        # Verify repository was called with correlation_id
        mock_repository.insert_health_checks.assert_called_once()
        call_kwargs = mock_repository.insert_health_checks.call_args[1]
        assert "correlation_id" in call_kwargs
        assert call_kwargs["correlation_id"] == correlation_id

    @pytest.mark.asyncio
    async def test_record_health_checks_without_correlation_id(self) -> None:
        """Test that endpoint works without correlation ID header.

        This ensures backward compatibility when correlation ID is not provided.
        """
        # Mock repository
        mock_repository = AsyncMock()
        mock_repository.insert_health_checks.return_value = 1

        # Create request
        request_data = {
            "checks": [
                {
                    "service_name": "database",
                    "service_type": "infrastructure",
                    "is_healthy": True,
                    "response_time_ms": 12.5,
                    "metadata": {},
                }
            ],
        }

        from src.api.routes.health import record_health_checks

        request = HealthCheckBatchRequest(**request_data)
        result = await record_health_checks(
            request=request, repository=mock_repository, correlation_id=None
        )

        # Verify response
        assert result.recorded == 1
        assert result.message == "Health checks recorded successfully"

        # Verify repository was called with None correlation_id
        mock_repository.insert_health_checks.assert_called_once()
        call_kwargs = mock_repository.insert_health_checks.call_args[1]
        assert "correlation_id" in call_kwargs
        assert call_kwargs["correlation_id"] is None

    @pytest.mark.asyncio
    @patch("src.api.routes.health.get_logger")
    async def test_record_health_checks_logs_with_correlation_id(
        self, mock_get_logger: MagicMock
    ) -> None:
        """Test that endpoint logs include correlation ID.

        Args:
            mock_get_logger: Mock logger factory
        """
        # Mock logger
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger

        # Mock repository
        mock_repository = AsyncMock()
        mock_repository.insert_health_checks.return_value = 2

        # Create request
        request_data = {
            "checks": [
                {
                    "service_name": "database",
                    "service_type": "infrastructure",
                    "is_healthy": True,
                    "response_time_ms": 12.5,
                    "metadata": {},
                }
            ],
        }

        correlation_id = "550e8400-e29b-41d4-a716-446655440000"

        from src.api.routes.health import record_health_checks

        request = HealthCheckBatchRequest(**request_data)
        result = await record_health_checks(
            request=request, repository=mock_repository, correlation_id=correlation_id
        )

        # Verify logger was called with correlation_id context
        mock_get_logger.assert_called_once()
        call_kwargs = mock_get_logger.call_args[1]
        assert "correlation_id" in call_kwargs
        assert call_kwargs["correlation_id"] == correlation_id

        # Verify INFO log was called
        assert mock_logger.info.called

    @pytest.mark.asyncio
    @patch("src.api.routes.health.get_logger")
    async def test_record_health_checks_logs_errors_with_correlation_id(
        self, mock_get_logger: MagicMock
    ) -> None:
        """Test that error logs include correlation ID.

        Args:
            mock_get_logger: Mock logger factory
        """
        # Mock logger
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger

        # Mock repository with failure
        mock_repository = AsyncMock()
        mock_repository.insert_health_checks.side_effect = Exception("Database error")

        # Create request
        request_data = {
            "checks": [
                {
                    "service_name": "database",
                    "service_type": "infrastructure",
                    "is_healthy": True,
                    "response_time_ms": 12.5,
                    "metadata": {},
                }
            ],
        }

        correlation_id = "550e8400-e29b-41d4-a716-446655440000"

        from src.api.routes.health import record_health_checks

        request = HealthCheckBatchRequest(**request_data)

        # Expect exception to be raised
        with pytest.raises(Exception):
            await record_health_checks(
                request=request, repository=mock_repository, correlation_id=correlation_id
            )

        # Verify logger was called with correlation_id
        mock_get_logger.assert_called_once()
        call_kwargs = mock_get_logger.call_args[1]
        assert "correlation_id" in call_kwargs
        assert call_kwargs["correlation_id"] == correlation_id
