"""Log service for business logic related to log management.

This module provides service-layer operations for log querying, analysis,
and management, following the Service pattern and SOLID principles.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from src.api.exceptions import ValidationError
from src.api.repositories.log_repository import LogRepository


class LogService:
    """Service for log management business logic.

    This class implements business logic for log operations, including
    validation, filtering, and coordination with the repository layer.
    """

    def __init__(self, repository: LogRepository) -> None:
        """Initialize log service with repository.

        Args:
            repository: Log repository instance
        """
        self.repository = repository

    async def get_logs(
        self,
        start_time: str | None = None,
        end_time: str | None = None,
        level: str | None = None,
        service: str | None = None,
        search: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> tuple[list[dict[str, Any]], int]:
        """Get logs with filters and pagination.

        Args:
            start_time: ISO format start time
            end_time: ISO format end time
            level: Log level filter
            service: Service name filter
            search: Search term
            limit: Page size
            offset: Pagination offset

        Returns:
            Tuple of (log list, total count estimate)

        Raises:
            ValidationError: If input validation fails
        """
        # Validate and parse timestamps
        start_dt = self._parse_timestamp(start_time) if start_time else None
        end_dt = self._parse_timestamp(end_time) if end_time else None

        # Validate log level
        if level:
            level = level.upper()
            if level not in ("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"):
                raise ValidationError(f"Invalid log level: {level}")

        # Validate limit and offset
        if limit < 1 or limit > 1000:
            raise ValidationError("Limit must be between 1 and 1000")
        if offset < 0:
            raise ValidationError("Offset must be non-negative")

        # Query logs
        logs = await self.repository.get_logs(
            start_time=start_dt,
            end_time=end_dt,
            level=level,
            service=service,
            search=search,
            limit=limit,
            offset=offset,
        )

        # For simplicity, we return the actual count as an estimate
        # In production, you might want a separate count query for large datasets
        total = len(logs) + offset if len(logs) == limit else offset + len(logs)

        return logs, total

    async def search_logs(
        self,
        search_term: str,
        limit: int = 100,
        offset: int = 0,
    ) -> tuple[list[dict[str, Any]], int]:
        """Full-text search in logs.

        Args:
            search_term: Search term
            limit: Page size
            offset: Pagination offset

        Returns:
            Tuple of (log list, total count estimate)

        Raises:
            ValidationError: If input validation fails
        """
        if not search_term or not search_term.strip():
            raise ValidationError("Search term cannot be empty")

        if limit < 1 or limit > 1000:
            raise ValidationError("Limit must be between 1 and 1000")
        if offset < 0:
            raise ValidationError("Offset must be non-negative")

        logs = await self.repository.search_logs(
            search_term=search_term.strip(),
            limit=limit,
            offset=offset,
        )

        total = len(logs) + offset if len(logs) == limit else offset + len(logs)

        return logs, total

    async def get_statistics(
        self,
        start_time: str | None = None,
        end_time: str | None = None,
    ) -> dict[str, Any]:
        """Get log statistics for a time range.

        Args:
            start_time: ISO format start time (default: 24 hours ago)
            end_time: ISO format end time (default: now)

        Returns:
            Statistics dictionary

        Raises:
            ValidationError: If input validation fails
        """
        start_dt = self._parse_timestamp(start_time) if start_time else None
        end_dt = self._parse_timestamp(end_time) if end_time else None

        return await self.repository.get_log_statistics(
            start_time=start_dt,
            end_time=end_dt,
        )

    async def get_related_logs(
        self,
        request_id: str | None = None,
        task_id: str | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """Get logs related by correlation IDs.

        Args:
            request_id: Request correlation ID
            task_id: Task correlation ID
            limit: Maximum results

        Returns:
            List of related logs

        Raises:
            ValidationError: If input validation fails
        """
        if not request_id and not task_id:
            raise ValidationError("Must provide either request_id or task_id")

        if limit < 1 or limit > 1000:
            raise ValidationError("Limit must be between 1 and 1000")

        # Parse UUIDs
        request_uuid = self._parse_uuid(request_id) if request_id else None
        task_uuid = self._parse_uuid(task_id) if task_id else None

        return await self.repository.get_related_logs(
            request_id=request_uuid,
            task_id=task_uuid,
            limit=limit,
        )

    async def get_log_by_id(self, log_id: int) -> dict[str, Any] | None:
        """Get a single log entry by ID.

        Args:
            log_id: Log entry ID

        Returns:
            Log entry or None

        Raises:
            ValidationError: If log_id is invalid
        """
        if log_id < 1:
            raise ValidationError("Log ID must be positive")

        return await self.repository.get_log_by_id(log_id)

    async def cleanup_old_logs(self, retention_days: int = 30) -> int:
        """Clean up logs older than retention period.

        Args:
            retention_days: Days to retain

        Returns:
            Number of deleted logs

        Raises:
            ValidationError: If retention_days is invalid
        """
        if retention_days < 1:
            raise ValidationError("Retention days must be positive")

        return await self.repository.cleanup_old_logs(retention_days)

    def _parse_timestamp(self, timestamp_str: str) -> datetime:
        """Parse ISO format timestamp string.

        Args:
            timestamp_str: ISO format timestamp

        Returns:
            Parsed datetime

        Raises:
            ValidationError: If timestamp format is invalid
        """
        try:
            # Try parsing with timezone
            if "T" in timestamp_str:
                return datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
            else:
                # Try parsing as date only
                return datetime.fromisoformat(timestamp_str)
        except ValueError:
            raise ValidationError(
                f"Invalid timestamp format: {timestamp_str}. Use ISO format (e.g., 2024-01-01T12:00:00Z)"
            )

    def _parse_uuid(self, uuid_str: str) -> UUID:
        """Parse UUID string.

        Args:
            uuid_str: UUID string

        Returns:
            Parsed UUID

        Raises:
            ValidationError: If UUID format is invalid
        """
        try:
            return UUID(uuid_str)
        except ValueError:
            raise ValidationError(f"Invalid UUID format: {uuid_str}")
