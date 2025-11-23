"""Unit tests for health check recording API endpoints.

This module tests the health check recording endpoints with mocked repository.
Following TDD principles, these tests define the expected behavior before implementation.
"""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import status

from src.api.models.schemas import (
    HealthCheckBatchRequest,
    HealthCheckQueryParams,
    HealthCheckRecord,
)


@pytest.fixture
def sample_batch_request() -> HealthCheckBatchRequest:
    """Create a sample batch request with health checks.

    Returns:
        Sample HealthCheckBatchRequest
    """
    return HealthCheckBatchRequest(
        checks=[
            HealthCheckRecord(
                service_name="database",
                service_type="infrastructure",
                is_healthy=True,
                response_time_ms=12.5,
                error_message=None,
                metadata={"version": "14.5"},
            ),
            HealthCheckRecord(
                service_name="api",
                service_type="application",
                is_healthy=True,
                response_time_ms=8.2,
                error_message=None,
                metadata={},
            ),
        ],
        timestamp=None,  # Will use current time
    )


class TestRecordHealthChecks:
    """Tests for POST /health/record endpoint."""

    @pytest.mark.asyncio
    async def test_record_health_checks_success(
        self, test_client, sample_batch_request: HealthCheckBatchRequest
    ) -> None:
        """Test successful health check recording.

        Args:
            test_client: FastAPI test client
            sample_batch_request: Sample batch request
        """
        with patch("src.api.routes.health.get_health_repository") as mock_repo_getter:
            mock_repo = AsyncMock()
            mock_repo.insert_health_checks = AsyncMock(return_value=2)
            mock_repo_getter.return_value = mock_repo

            response = test_client.post("/health/record", json=sample_batch_request.model_dump())

            assert response.status_code == status.HTTP_201_CREATED
            data = response.json()
            assert data["recorded"] == 2
            assert "timestamp" in data
            assert data["message"] == "Health checks recorded successfully"

    @pytest.mark.asyncio
    async def test_record_health_checks_with_custom_timestamp(
        self, test_client, sample_batch_request: HealthCheckBatchRequest
    ) -> None:
        """Test recording health checks with custom timestamp.

        Args:
            test_client: FastAPI test client
            sample_batch_request: Sample batch request
        """
        custom_timestamp = "2024-01-15T10:30:00Z"
        sample_batch_request.timestamp = custom_timestamp

        with patch("src.api.routes.health.get_health_repository") as mock_repo_getter:
            mock_repo = AsyncMock()
            mock_repo.insert_health_checks = AsyncMock(return_value=2)
            mock_repo_getter.return_value = mock_repo

            response = test_client.post("/health/record", json=sample_batch_request.model_dump())

            assert response.status_code == status.HTTP_201_CREATED
            data = response.json()
            assert custom_timestamp in data["timestamp"]

    @pytest.mark.asyncio
    async def test_record_health_checks_empty_list(self, test_client) -> None:
        """Test recording empty list of health checks.

        Args:
            test_client: FastAPI test client
        """
        empty_request = HealthCheckBatchRequest(checks=[], timestamp=None)

        with patch("src.api.routes.health.get_health_repository") as mock_repo_getter:
            mock_repo = AsyncMock()
            mock_repo.insert_health_checks = AsyncMock(return_value=0)
            mock_repo_getter.return_value = mock_repo

            response = test_client.post("/health/record", json=empty_request.model_dump())

            assert response.status_code == status.HTTP_201_CREATED
            data = response.json()
            assert data["recorded"] == 0

    @pytest.mark.asyncio
    async def test_record_health_checks_validation_error(self, test_client) -> None:
        """Test validation error with invalid request.

        Args:
            test_client: FastAPI test client
        """
        invalid_request = {"checks": [{"invalid": "data"}]}

        response = test_client.post("/health/record", json=invalid_request)

        # Should return 422 for validation error
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


class TestGetHealthHistory:
    """Tests for GET /health/history endpoint."""

    @pytest.mark.asyncio
    async def test_get_health_history_success(self, test_client) -> None:
        """Test successful health history retrieval.

        Args:
            test_client: FastAPI test client
        """
        with patch("src.api.routes.health.get_health_repository") as mock_repo_getter:
            mock_repo = AsyncMock()
            mock_repo.query_health_history = AsyncMock(
                return_value=[
                    {
                        "id": 1,
                        "timestamp": "2024-01-15T10:00:00+00:00",
                        "service_name": "database",
                        "service_type": "infrastructure",
                        "is_healthy": True,
                        "response_time_ms": 10.5,
                        "error_message": None,
                        "metadata": {},
                    }
                ]
            )
            mock_repo_getter.return_value = mock_repo

            response = test_client.get(
                "/health/history",
                params={
                    "start_time": "2024-01-15T00:00:00Z",
                    "end_time": "2024-01-15T23:59:59Z",
                },
            )

            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert "records" in data
            assert "total" in data
            assert len(data["records"]) == 1
            assert data["total"] == 1

    @pytest.mark.asyncio
    async def test_get_health_history_with_filters(self, test_client) -> None:
        """Test health history with service filters.

        Args:
            test_client: FastAPI test client
        """
        with patch("src.api.routes.health.get_health_repository") as mock_repo_getter:
            mock_repo = AsyncMock()
            mock_repo.query_health_history = AsyncMock(return_value=[])
            mock_repo_getter.return_value = mock_repo

            response = test_client.get(
                "/health/history",
                params={
                    "start_time": "2024-01-15T00:00:00Z",
                    "end_time": "2024-01-15T23:59:59Z",
                    "service_names": ["database", "api"],
                    "service_type": "infrastructure",
                },
            )

            assert response.status_code == status.HTTP_200_OK

    @pytest.mark.asyncio
    async def test_get_health_history_missing_required_params(self, test_client) -> None:
        """Test health history with missing required parameters.

        Args:
            test_client: FastAPI test client
        """
        # Missing start_time and end_time
        response = test_client.get("/health/history")

        # Should return 422 for missing required fields
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


class TestGetLatestHealth:
    """Tests for GET /health/latest endpoint."""

    @pytest.mark.asyncio
    async def test_get_latest_health_success(self, test_client) -> None:
        """Test successful latest health status retrieval.

        Args:
            test_client: FastAPI test client
        """
        with patch("src.api.routes.health.get_health_repository") as mock_repo_getter:
            mock_repo = AsyncMock()
            mock_repo.get_latest_health_status = AsyncMock(
                return_value={
                    "database": True,
                    "api": True,
                    "worker": False,
                    "storage": True,
                }
            )
            mock_repo_getter.return_value = mock_repo

            response = test_client.get("/health/latest")

            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert "services" in data
            assert "timestamp" in data
            assert data["services"]["database"] is True
            assert data["services"]["worker"] is False

    @pytest.mark.asyncio
    async def test_get_latest_health_no_data(self, test_client) -> None:
        """Test latest health status when no data exists.

        Args:
            test_client: FastAPI test client
        """
        with patch("src.api.routes.health.get_health_repository") as mock_repo_getter:
            mock_repo = AsyncMock()
            mock_repo.get_latest_health_status = AsyncMock(return_value={})
            mock_repo_getter.return_value = mock_repo

            response = test_client.get("/health/latest")

            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["services"] == {}
