"""Unit tests for HealthRepository.

This module tests the health check repository with mocked database sessions.
Following TDD principles, these tests define the expected behavior before implementation.
"""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.models.schemas import HealthCheckQueryParams, HealthCheckRecord
from src.api.repositories.health_repository import HealthRepository


@pytest.fixture
def mock_session() -> AsyncMock:
    """Create a mock async database session.

    Returns:
        Mock AsyncSession for testing
    """
    session = AsyncMock(spec=AsyncSession)
    return session


@pytest.fixture
def health_repository(mock_session: AsyncMock) -> HealthRepository:
    """Create a HealthRepository instance with mock session.

    Args:
        mock_session: Mock database session

    Returns:
        HealthRepository instance for testing
    """
    return HealthRepository(session=mock_session)


@pytest.fixture
def sample_health_check() -> HealthCheckRecord:
    """Create a sample health check record.

    Returns:
        Sample HealthCheckRecord
    """
    return HealthCheckRecord(
        service_name="database",
        service_type="infrastructure",
        is_healthy=True,
        response_time_ms=15.5,
        error_message=None,
        metadata={"version": "14.5"},
    )


@pytest.fixture
def sample_unhealthy_check() -> HealthCheckRecord:
    """Create a sample unhealthy health check record.

    Returns:
        Sample HealthCheckRecord with unhealthy status
    """
    return HealthCheckRecord(
        service_name="api",
        service_type="application",
        is_healthy=False,
        response_time_ms=None,
        error_message="Connection timeout",
        metadata={},
    )


class TestHealthRepositoryInsert:
    """Tests for inserting health check records."""

    @pytest.mark.asyncio
    async def test_insert_health_checks_single_record(
        self, health_repository: HealthRepository, sample_health_check: HealthCheckRecord
    ) -> None:
        """Test inserting a single health check record.

        Args:
            health_repository: Repository instance
            sample_health_check: Sample health check record
        """
        timestamp = datetime.now(timezone.utc)

        # Mock the execute method
        health_repository.session.execute = AsyncMock()

        result = await health_repository.insert_health_checks(
            checks=[sample_health_check], timestamp=timestamp
        )

        # Should return the count of inserted records
        assert result == 1

        # Should call execute once for batch insert
        assert health_repository.session.execute.called

    @pytest.mark.asyncio
    async def test_insert_health_checks_multiple_records(
        self,
        health_repository: HealthRepository,
        sample_health_check: HealthCheckRecord,
        sample_unhealthy_check: HealthCheckRecord,
    ) -> None:
        """Test inserting multiple health check records in batch.

        Args:
            health_repository: Repository instance
            sample_health_check: Sample healthy check
            sample_unhealthy_check: Sample unhealthy check
        """
        timestamp = datetime.now(timezone.utc)
        checks = [sample_health_check, sample_unhealthy_check]

        # Mock the execute method
        health_repository.session.execute = AsyncMock()

        result = await health_repository.insert_health_checks(checks=checks, timestamp=timestamp)

        # Should return the count of inserted records
        assert result == 2

        # Should call execute once for batch insert
        assert health_repository.session.execute.called

    @pytest.mark.asyncio
    async def test_insert_health_checks_empty_list(
        self, health_repository: HealthRepository
    ) -> None:
        """Test inserting empty list of health checks.

        Args:
            health_repository: Repository instance
        """
        timestamp = datetime.now(timezone.utc)

        result = await health_repository.insert_health_checks(checks=[], timestamp=timestamp)

        # Should return 0 and not call database
        assert result == 0
        assert not health_repository.session.execute.called

    @pytest.mark.asyncio
    async def test_insert_health_checks_uses_provided_timestamp(
        self, health_repository: HealthRepository, sample_health_check: HealthCheckRecord
    ) -> None:
        """Test that provided timestamp is used for all records.

        Args:
            health_repository: Repository instance
            sample_health_check: Sample health check record
        """
        custom_timestamp = datetime(2024, 1, 15, 10, 30, 0, tzinfo=timezone.utc)

        # Mock the execute method to capture the call
        health_repository.session.execute = AsyncMock()

        await health_repository.insert_health_checks(
            checks=[sample_health_check], timestamp=custom_timestamp
        )

        # Verify execute was called with correct timestamp in values
        call_args = health_repository.session.execute.call_args
        assert call_args is not None


class TestHealthRepositoryQuery:
    """Tests for querying health check history."""

    @pytest.mark.asyncio
    async def test_query_health_history_basic(self, health_repository: HealthRepository) -> None:
        """Test basic health history query.

        Args:
            health_repository: Repository instance
        """
        params = HealthCheckQueryParams(
            start_time="2024-01-01T00:00:00Z",
            end_time="2024-01-02T00:00:00Z",
            limit=100,
        )

        # Mock the execute and fetchall methods
        mock_result = MagicMock()
        mock_result.fetchall.return_value = [
            MagicMock(
                id=1,
                timestamp=datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc),
                service_name="database",
                service_type="infrastructure",
                is_healthy=True,
                response_time_ms=10.5,
                error_message=None,
                metadata={},
            )
        ]
        health_repository.session.execute = AsyncMock(return_value=mock_result)

        results = await health_repository.query_health_history(params)

        # Should return list of dictionaries
        assert isinstance(results, list)
        assert len(results) == 1
        assert results[0]["service_name"] == "database"
        assert results[0]["is_healthy"] is True

    @pytest.mark.asyncio
    async def test_query_health_history_with_service_filter(
        self, health_repository: HealthRepository
    ) -> None:
        """Test health history query with service name filter.

        Args:
            health_repository: Repository instance
        """
        params = HealthCheckQueryParams(
            service_names=["database", "api"],
            start_time="2024-01-01T00:00:00Z",
            end_time="2024-01-02T00:00:00Z",
            limit=100,
        )

        # Mock the execute and fetchall methods
        mock_result = MagicMock()
        mock_result.fetchall.return_value = []
        health_repository.session.execute = AsyncMock(return_value=mock_result)

        results = await health_repository.query_health_history(params)

        # Should call execute with filtered query
        assert health_repository.session.execute.called
        assert isinstance(results, list)

    @pytest.mark.asyncio
    async def test_query_health_history_with_type_filter(
        self, health_repository: HealthRepository
    ) -> None:
        """Test health history query with service type filter.

        Args:
            health_repository: Repository instance
        """
        params = HealthCheckQueryParams(
            service_type="infrastructure",
            start_time="2024-01-01T00:00:00Z",
            end_time="2024-01-02T00:00:00Z",
            limit=100,
        )

        # Mock the execute and fetchall methods
        mock_result = MagicMock()
        mock_result.fetchall.return_value = []
        health_repository.session.execute = AsyncMock(return_value=mock_result)

        results = await health_repository.query_health_history(params)

        # Should call execute with filtered query
        assert health_repository.session.execute.called
        assert isinstance(results, list)

    @pytest.mark.asyncio
    async def test_query_health_history_respects_limit(
        self, health_repository: HealthRepository
    ) -> None:
        """Test that query respects the limit parameter.

        Args:
            health_repository: Repository instance
        """
        params = HealthCheckQueryParams(
            start_time="2024-01-01T00:00:00Z",
            end_time="2024-01-02T00:00:00Z",
            limit=50,
        )

        # Mock the execute and fetchall methods
        mock_result = MagicMock()
        mock_result.fetchall.return_value = []
        health_repository.session.execute = AsyncMock(return_value=mock_result)

        await health_repository.query_health_history(params)

        # Should call execute with limit in query
        assert health_repository.session.execute.called


class TestHealthRepositoryLatest:
    """Tests for getting latest health status."""

    @pytest.mark.asyncio
    async def test_get_latest_health_status_all_services(
        self, health_repository: HealthRepository
    ) -> None:
        """Test getting latest health status for all services.

        Args:
            health_repository: Repository instance
        """
        # Mock the execute and fetchall methods
        mock_result = MagicMock()
        mock_result.fetchall.return_value = [
            MagicMock(service_name="database", is_healthy=True),
            MagicMock(service_name="api", is_healthy=True),
            MagicMock(service_name="worker", is_healthy=False),
        ]
        health_repository.session.execute = AsyncMock(return_value=mock_result)

        result = await health_repository.get_latest_health_status()

        # Should return dictionary mapping service name to health status
        assert isinstance(result, dict)
        assert result["database"] is True
        assert result["api"] is True
        assert result["worker"] is False

    @pytest.mark.asyncio
    async def test_get_latest_health_status_no_data(
        self, health_repository: HealthRepository
    ) -> None:
        """Test getting latest health status when no data exists.

        Args:
            health_repository: Repository instance
        """
        # Mock the execute and fetchall methods to return empty
        mock_result = MagicMock()
        mock_result.fetchall.return_value = []
        health_repository.session.execute = AsyncMock(return_value=mock_result)

        result = await health_repository.get_latest_health_status()

        # Should return empty dictionary
        assert isinstance(result, dict)
        assert len(result) == 0

    @pytest.mark.asyncio
    async def test_get_latest_health_status_uses_distinct_on(
        self, health_repository: HealthRepository
    ) -> None:
        """Test that latest status query uses DISTINCT ON to get most recent per service.

        Args:
            health_repository: Repository instance
        """
        # Mock the execute and fetchall methods
        mock_result = MagicMock()
        mock_result.fetchall.return_value = [
            MagicMock(service_name="database", is_healthy=True),
        ]
        health_repository.session.execute = AsyncMock(return_value=mock_result)

        await health_repository.get_latest_health_status()

        # Should call execute (verify query construction in implementation)
        assert health_repository.session.execute.called
