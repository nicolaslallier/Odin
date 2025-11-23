"""Integration tests for health check timeseries functionality.

This module tests end-to-end health check recording and querying
with real database operations.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import text

from src.api.models.schemas import (
    HealthCheckBatchRequest,
    HealthCheckQueryParams,
    HealthCheckRecord,
)
from src.api.repositories.health_repository import HealthRepository


@pytest.mark.asyncio
@pytest.mark.integration
class TestHealthCheckIntegration:
    """Integration tests for health check timeseries."""

    async def test_insert_and_query_health_checks(self, db_session) -> None:
        """Test inserting and querying health check records.

        Args:
            db_session: Test database session
        """
        repository = HealthRepository(session=db_session)

        # Create test data
        timestamp = datetime.now(timezone.utc)
        checks = [
            HealthCheckRecord(
                service_name="database",
                service_type="infrastructure",
                is_healthy=True,
                response_time_ms=10.5,
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
        ]

        # Insert health checks
        count = await repository.insert_health_checks(checks, timestamp)
        assert count == 2

        # Query health checks
        start_time = (timestamp - timedelta(minutes=1)).isoformat()
        end_time = (timestamp + timedelta(minutes=1)).isoformat()

        params = HealthCheckQueryParams(
            start_time=start_time,
            end_time=end_time,
            limit=100,
        )

        results = await repository.query_health_history(params)

        # Verify results
        assert len(results) == 2
        assert any(r["service_name"] == "database" for r in results)
        assert any(r["service_name"] == "api" for r in results)

    async def test_query_with_service_filter(self, db_session) -> None:
        """Test querying with service name filter.

        Args:
            db_session: Test database session
        """
        repository = HealthRepository(session=db_session)

        # Insert test data
        timestamp = datetime.now(timezone.utc)
        checks = [
            HealthCheckRecord(
                service_name="database",
                service_type="infrastructure",
                is_healthy=True,
                response_time_ms=10.5,
                error_message=None,
                metadata={},
            ),
            HealthCheckRecord(
                service_name="storage",
                service_type="infrastructure",
                is_healthy=False,
                response_time_ms=None,
                error_message="Connection timeout",
                metadata={},
            ),
        ]

        await repository.insert_health_checks(checks, timestamp)

        # Query with filter
        start_time = (timestamp - timedelta(minutes=1)).isoformat()
        end_time = (timestamp + timedelta(minutes=1)).isoformat()

        params = HealthCheckQueryParams(
            service_names=["database"],
            start_time=start_time,
            end_time=end_time,
            limit=100,
        )

        results = await repository.query_health_history(params)

        # Should only return database records
        assert all(r["service_name"] == "database" for r in results)

    async def test_get_latest_health_status(self, db_session) -> None:
        """Test getting latest health status for services.

        Args:
            db_session: Test database session
        """
        repository = HealthRepository(session=db_session)

        # Insert older data
        old_timestamp = datetime.now(timezone.utc) - timedelta(minutes=5)
        old_checks = [
            HealthCheckRecord(
                service_name="database",
                service_type="infrastructure",
                is_healthy=False,  # Old status: unhealthy
                response_time_ms=None,
                error_message="Old error",
                metadata={},
            ),
        ]
        await repository.insert_health_checks(old_checks, old_timestamp)

        # Insert newer data
        new_timestamp = datetime.now(timezone.utc)
        new_checks = [
            HealthCheckRecord(
                service_name="database",
                service_type="infrastructure",
                is_healthy=True,  # New status: healthy
                response_time_ms=10.5,
                error_message=None,
                metadata={},
            ),
            HealthCheckRecord(
                service_name="api",
                service_type="application",
                is_healthy=True,
                response_time_ms=8.2,
                error_message=None,
                metadata={},
            ),
        ]
        await repository.insert_health_checks(new_checks, new_timestamp)

        # Get latest status
        status = await repository.get_latest_health_status()

        # Should return newest status
        assert status["database"] is True  # Not False from old data
        assert status["api"] is True

    async def test_query_with_time_range(self, db_session) -> None:
        """Test querying with specific time range.

        Args:
            db_session: Test database session
        """
        repository = HealthRepository(session=db_session)

        # Insert data at different times
        base_time = datetime.now(timezone.utc)

        # Old data (outside range)
        old_time = base_time - timedelta(hours=2)
        old_checks = [
            HealthCheckRecord(
                service_name="old_service",
                service_type="infrastructure",
                is_healthy=True,
                response_time_ms=10.0,
                error_message=None,
                metadata={},
            ),
        ]
        await repository.insert_health_checks(old_checks, old_time)

        # Recent data (inside range)
        recent_time = base_time - timedelta(minutes=30)
        recent_checks = [
            HealthCheckRecord(
                service_name="recent_service",
                service_type="infrastructure",
                is_healthy=True,
                response_time_ms=10.0,
                error_message=None,
                metadata={},
            ),
        ]
        await repository.insert_health_checks(recent_checks, recent_time)

        # Query only recent data
        start_time = (base_time - timedelta(hours=1)).isoformat()
        end_time = base_time.isoformat()

        params = HealthCheckQueryParams(
            start_time=start_time,
            end_time=end_time,
            limit=100,
        )

        results = await repository.query_health_history(params)

        # Should only return recent data
        assert all(r["service_name"] == "recent_service" for r in results)
        assert not any(r["service_name"] == "old_service" for r in results)

    async def test_query_respects_limit(self, db_session) -> None:
        """Test that query respects the limit parameter.

        Args:
            db_session: Test database session
        """
        repository = HealthRepository(session=db_session)

        # Insert many records
        timestamp = datetime.now(timezone.utc)
        checks = [
            HealthCheckRecord(
                service_name=f"service_{i}",
                service_type="infrastructure",
                is_healthy=True,
                response_time_ms=10.0,
                error_message=None,
                metadata={},
            )
            for i in range(20)
        ]
        await repository.insert_health_checks(checks, timestamp)

        # Query with limit
        start_time = (timestamp - timedelta(minutes=1)).isoformat()
        end_time = (timestamp + timedelta(minutes=1)).isoformat()

        params = HealthCheckQueryParams(
            start_time=start_time,
            end_time=end_time,
            limit=5,
        )

        results = await repository.query_health_history(params)

        # Should respect limit
        assert len(results) <= 5
