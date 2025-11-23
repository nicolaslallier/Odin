"""Repository for health check data persistence.

This module provides data access operations for health check records using
the repository pattern to abstract TimescaleDB operations.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    Float,
    Integer,
    MetaData,
    String,
    Table,
    Text,
    insert,
    select,
    TIMESTAMP,
)
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.exceptions import DatabaseError
from src.api.models.schemas import HealthCheckQueryParams, HealthCheckRecord

# Define the service_health_checks table
metadata = MetaData()

service_health_checks_table = Table(
    "service_health_checks",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("timestamp", TIMESTAMP(timezone=True), nullable=False, primary_key=True),
    Column("service_name", String(255), nullable=False),
    Column("service_type", String(50), nullable=False),
    Column("is_healthy", Boolean, nullable=False),
    Column("response_time_ms", Float, nullable=True),
    Column("error_message", Text, nullable=True),
    Column("metadata", JSON, nullable=False, server_default="{}"),
)


class HealthRepository:
    """Repository for health check data access operations.

    This class implements the Repository pattern for health check related database
    operations using TimescaleDB hypertable for efficient time-series storage.

    Attributes:
        session: SQLAlchemy async session for database operations
    """

    def __init__(self, session: AsyncSession) -> None:
        """Initialize the health repository.

        Args:
            session: SQLAlchemy async session
        """
        self.session = session

    async def insert_health_checks(
        self, checks: list[HealthCheckRecord], timestamp: datetime
    ) -> int:
        """Insert batch of health check records into TimescaleDB.

        This method performs a batch insert of health check records with the
        provided timestamp, optimizing for write performance.

        Args:
            checks: List of health check records to insert
            timestamp: Timestamp to use for all records

        Returns:
            Number of records inserted

        Raises:
            DatabaseError: If insertion fails

        Example:
            >>> checks = [HealthCheckRecord(...), HealthCheckRecord(...)]
            >>> count = await repo.insert_health_checks(checks, datetime.now())
        """
        if not checks:
            return 0

        try:
            # Prepare batch insert values
            values = [
                {
                    "timestamp": timestamp,
                    "service_name": check.service_name,
                    "service_type": check.service_type,
                    "is_healthy": check.is_healthy,
                    "response_time_ms": check.response_time_ms,
                    "error_message": check.error_message,
                    "metadata": check.metadata,
                }
                for check in checks
            ]

            # Execute batch insert
            stmt = insert(service_health_checks_table).values(values)
            await self.session.execute(stmt)

            return len(checks)

        except Exception as e:
            raise DatabaseError(f"Failed to insert health checks: {e}")

    async def query_health_history(self, params: HealthCheckQueryParams) -> list[dict[str, any]]:
        """Query health check history with filters.

        This method retrieves historical health check data from TimescaleDB
        with optional filtering by service name, service type, and time range.

        Args:
            params: Query parameters including filters and limits

        Returns:
            List of health check records as dictionaries

        Raises:
            DatabaseError: If query fails

        Example:
            >>> params = HealthCheckQueryParams(
            ...     start_time="2024-01-01T00:00:00Z",
            ...     end_time="2024-01-02T00:00:00Z",
            ...     service_names=["database"],
            ...     limit=100
            ... )
            >>> records = await repo.query_health_history(params)
        """
        try:
            # Parse ISO datetime strings
            start_dt = datetime.fromisoformat(params.start_time.replace("Z", "+00:00"))
            end_dt = datetime.fromisoformat(params.end_time.replace("Z", "+00:00"))

            # Build base query
            query = select(service_health_checks_table).where(
                service_health_checks_table.c.timestamp >= start_dt,
                service_health_checks_table.c.timestamp <= end_dt,
            )

            # Add service name filter if specified
            if params.service_names:
                query = query.where(
                    service_health_checks_table.c.service_name.in_(params.service_names)
                )

            # Add service type filter if specified
            if params.service_type:
                query = query.where(
                    service_health_checks_table.c.service_type == params.service_type
                )

            # Order by timestamp descending and apply limit
            query = query.order_by(service_health_checks_table.c.timestamp.desc()).limit(
                params.limit
            )

            # Execute query
            result = await self.session.execute(query)
            rows = result.fetchall()

            # Convert rows to dictionaries
            return [
                {
                    "id": row.id,
                    "timestamp": row.timestamp.isoformat(),
                    "service_name": row.service_name,
                    "service_type": row.service_type,
                    "is_healthy": row.is_healthy,
                    "response_time_ms": row.response_time_ms,
                    "error_message": row.error_message,
                    "metadata": row.metadata,
                }
                for row in rows
            ]

        except Exception as e:
            raise DatabaseError(f"Failed to query health history: {e}")

    async def get_latest_health_status(self) -> dict[str, bool]:
        """Get the latest health status for all services.

        This method retrieves the most recent health check result for each
        service using PostgreSQL DISTINCT ON for efficient querying.

        Returns:
            Dictionary mapping service name to latest health status

        Raises:
            DatabaseError: If query fails

        Example:
            >>> status = await repo.get_latest_health_status()
            >>> print(status)
            {'database': True, 'api': True, 'worker': False}
        """
        try:
            # Use PostgreSQL DISTINCT ON to get latest record per service
            # Note: This requires ordering by service_name first, then timestamp desc
            query = (
                select(
                    service_health_checks_table.c.service_name,
                    service_health_checks_table.c.is_healthy,
                )
                .distinct(service_health_checks_table.c.service_name)
                .order_by(
                    service_health_checks_table.c.service_name,
                    service_health_checks_table.c.timestamp.desc(),
                )
            )

            result = await self.session.execute(query)
            rows = result.fetchall()

            # Convert to dictionary
            return {row.service_name: row.is_healthy for row in rows}

        except Exception as e:
            raise DatabaseError(f"Failed to get latest health status: {e}")
