"""Log repository for database operations on application logs.

This module provides data access methods for querying, searching, and
managing application logs in PostgreSQL.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.exceptions import DatabaseError


class LogRepository:
    """Repository for log data access operations.

    This class implements the Repository pattern for log-related database
    operations, following the Single Responsibility Principle.
    """

    def __init__(self, session: AsyncSession) -> None:
        """Initialize log repository with database session.

        Args:
            session: SQLAlchemy async session
        """
        self.session = session

    async def get_logs(
        self,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        level: str | None = None,
        service: str | None = None,
        search: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        """Get logs with optional filters.

        Args:
            start_time: Filter logs after this timestamp
            end_time: Filter logs before this timestamp
            level: Filter by log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
            service: Filter by service name (api, worker, web, nginx)
            search: Search term for message content
            limit: Maximum number of results
            offset: Offset for pagination

        Returns:
            List of log entries as dictionaries

        Raises:
            DatabaseError: If query fails
        """
        try:
            # Build WHERE clauses
            where_clauses = []
            params = {}

            if start_time:
                where_clauses.append("timestamp >= :start_time")
                params["start_time"] = start_time

            if end_time:
                where_clauses.append("timestamp <= :end_time")
                params["end_time"] = end_time

            if level:
                where_clauses.append("level = :level")
                params["level"] = level.upper()

            if service:
                where_clauses.append("service = :service")
                params["service"] = service

            if search:
                where_clauses.append(
                    "(message ILIKE :search OR to_tsvector('english', message) @@ plainto_tsquery('english', :search_fts))"
                )
                params["search"] = f"%{search}%"
                params["search_fts"] = search

            where_clause = " AND ".join(where_clauses) if where_clauses else "1=1"

            # Build query
            query = text(
                f"""
                SELECT
                    id,
                    timestamp,
                    level,
                    service,
                    logger,
                    message,
                    module,
                    function,
                    line,
                    exception,
                    request_id,
                    task_id,
                    user_id,
                    metadata,
                    created_at
                FROM application_logs
                WHERE {where_clause}
                ORDER BY timestamp DESC
                LIMIT :limit OFFSET :offset
            """
            )

            params["limit"] = limit
            params["offset"] = offset

            result = await self.session.execute(query, params)
            rows = result.fetchall()

            return [
                {
                    "id": row[0],
                    "timestamp": row[1].isoformat() if row[1] else None,
                    "level": row[2],
                    "service": row[3],
                    "logger": row[4],
                    "message": row[5],
                    "module": row[6],
                    "function": row[7],
                    "line": row[8],
                    "exception": row[9],
                    "request_id": str(row[10]) if row[10] else None,
                    "task_id": str(row[11]) if row[11] else None,
                    "user_id": row[12],
                    "metadata": row[13] or {},
                    "created_at": row[14].isoformat() if row[14] else None,
                }
                for row in rows
            ]

        except Exception as e:
            raise DatabaseError(f"Failed to query logs: {e}")

    async def search_logs(
        self,
        search_term: str,
        limit: int = 100,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        """Full-text search in log messages.

        Args:
            search_term: Search term for full-text search
            limit: Maximum number of results
            offset: Offset for pagination

        Returns:
            List of matching log entries

        Raises:
            DatabaseError: If query fails
        """
        try:
            query = text(
                """
                SELECT
                    id,
                    timestamp,
                    level,
                    service,
                    logger,
                    message,
                    module,
                    function,
                    line,
                    exception,
                    request_id,
                    task_id,
                    user_id,
                    metadata,
                    created_at,
                    ts_rank(to_tsvector('english', message), plainto_tsquery('english', :search)) as rank
                FROM application_logs
                WHERE to_tsvector('english', message) @@ plainto_tsquery('english', :search)
                ORDER BY rank DESC, timestamp DESC
                LIMIT :limit OFFSET :offset
            """
            )

            result = await self.session.execute(
                query, {"search": search_term, "limit": limit, "offset": offset}
            )
            rows = result.fetchall()

            return [
                {
                    "id": row[0],
                    "timestamp": row[1].isoformat() if row[1] else None,
                    "level": row[2],
                    "service": row[3],
                    "logger": row[4],
                    "message": row[5],
                    "module": row[6],
                    "function": row[7],
                    "line": row[8],
                    "exception": row[9],
                    "request_id": str(row[10]) if row[10] else None,
                    "task_id": str(row[11]) if row[11] else None,
                    "user_id": row[12],
                    "metadata": row[13] or {},
                    "created_at": row[14].isoformat() if row[14] else None,
                    "rank": float(row[15]),
                }
                for row in rows
            ]

        except Exception as e:
            raise DatabaseError(f"Failed to search logs: {e}")

    async def get_log_statistics(
        self,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
    ) -> dict[str, Any]:
        """Get aggregated log statistics.

        Args:
            start_time: Start of time range (default: 24 hours ago)
            end_time: End of time range (default: now)

        Returns:
            Dictionary with aggregated statistics

        Raises:
            DatabaseError: If query fails
        """
        if not start_time:
            start_time = datetime.utcnow() - timedelta(hours=24)
        if not end_time:
            end_time = datetime.utcnow()

        try:
            # Get statistics by service and level
            query = text(
                """
                SELECT * FROM get_log_statistics(:start_time, :end_time)
            """
            )

            result = await self.session.execute(
                query, {"start_time": start_time, "end_time": end_time}
            )
            rows = result.fetchall()

            stats_by_service = {}
            for row in rows:
                service = row[0]
                level = row[1]
                count = row[2]
                latest = row[3]

                if service not in stats_by_service:
                    stats_by_service[service] = {}

                stats_by_service[service][level] = {
                    "count": count,
                    "latest_timestamp": latest.isoformat() if latest else None,
                }

            # Get total counts
            total_query = text(
                """
                SELECT
                    COUNT(*) as total,
                    COUNT(CASE WHEN level = 'DEBUG' THEN 1 END) as debug,
                    COUNT(CASE WHEN level = 'INFO' THEN 1 END) as info,
                    COUNT(CASE WHEN level = 'WARNING' THEN 1 END) as warning,
                    COUNT(CASE WHEN level = 'ERROR' THEN 1 END) as error,
                    COUNT(CASE WHEN level = 'CRITICAL' THEN 1 END) as critical
                FROM application_logs
                WHERE timestamp BETWEEN :start_time AND :end_time
            """
            )

            result = await self.session.execute(
                total_query, {"start_time": start_time, "end_time": end_time}
            )
            row = result.fetchone()

            return {
                "time_range": {
                    "start": start_time.isoformat(),
                    "end": end_time.isoformat(),
                },
                "total_logs": row[0] if row else 0,
                "by_level": {
                    "DEBUG": row[1] if row else 0,
                    "INFO": row[2] if row else 0,
                    "WARNING": row[3] if row else 0,
                    "ERROR": row[4] if row else 0,
                    "CRITICAL": row[5] if row else 0,
                },
                "by_service": stats_by_service,
            }

        except Exception as e:
            raise DatabaseError(f"Failed to get log statistics: {e}")

    async def cleanup_old_logs(self, retention_days: int = 30) -> int:
        """Delete logs older than retention period.

        Args:
            retention_days: Number of days to retain logs

        Returns:
            Number of deleted log entries

        Raises:
            DatabaseError: If cleanup fails
        """
        try:
            query = text(
                """
                SELECT * FROM cleanup_old_logs(:retention_days)
            """
            )

            result = await self.session.execute(query, {"retention_days": retention_days})
            row = result.fetchone()
            await self.session.commit()

            return row[0] if row else 0

        except Exception as e:
            await self.session.rollback()
            raise DatabaseError(f"Failed to cleanup old logs: {e}")

    async def get_related_logs(
        self,
        request_id: UUID | None = None,
        task_id: UUID | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """Find logs related by request_id or task_id.

        Args:
            request_id: Request correlation ID
            task_id: Task correlation ID
            limit: Maximum number of results

        Returns:
            List of related log entries

        Raises:
            DatabaseError: If query fails
        """
        if not request_id and not task_id:
            return []

        try:
            where_clauses = []
            params = {}

            if request_id:
                where_clauses.append("request_id = :request_id")
                params["request_id"] = str(request_id)

            if task_id:
                where_clauses.append("task_id = :task_id")
                params["task_id"] = str(task_id)

            where_clause = " OR ".join(where_clauses)

            query = text(
                f"""
                SELECT
                    id,
                    timestamp,
                    level,
                    service,
                    logger,
                    message,
                    module,
                    function,
                    line,
                    exception,
                    request_id,
                    task_id,
                    user_id,
                    metadata,
                    created_at
                FROM application_logs
                WHERE {where_clause}
                ORDER BY timestamp ASC
                LIMIT :limit
            """
            )

            params["limit"] = limit

            result = await self.session.execute(query, params)
            rows = result.fetchall()

            return [
                {
                    "id": row[0],
                    "timestamp": row[1].isoformat() if row[1] else None,
                    "level": row[2],
                    "service": row[3],
                    "logger": row[4],
                    "message": row[5],
                    "module": row[6],
                    "function": row[7],
                    "line": row[8],
                    "exception": row[9],
                    "request_id": str(row[10]) if row[10] else None,
                    "task_id": str(row[11]) if row[11] else None,
                    "user_id": row[12],
                    "metadata": row[13] or {},
                    "created_at": row[14].isoformat() if row[14] else None,
                }
                for row in rows
            ]

        except Exception as e:
            raise DatabaseError(f"Failed to get related logs: {e}")

    async def get_log_by_id(self, log_id: int) -> dict[str, Any] | None:
        """Get a single log entry by ID.

        Args:
            log_id: Log entry ID

        Returns:
            Log entry dictionary or None if not found

        Raises:
            DatabaseError: If query fails
        """
        try:
            query = text(
                """
                SELECT
                    id,
                    timestamp,
                    level,
                    service,
                    logger,
                    message,
                    module,
                    function,
                    line,
                    exception,
                    request_id,
                    task_id,
                    user_id,
                    metadata,
                    created_at
                FROM application_logs
                WHERE id = :log_id
            """
            )

            result = await self.session.execute(query, {"log_id": log_id})
            row = result.fetchone()

            if not row:
                return None

            return {
                "id": row[0],
                "timestamp": row[1].isoformat() if row[1] else None,
                "level": row[2],
                "service": row[3],
                "logger": row[4],
                "message": row[5],
                "module": row[6],
                "function": row[7],
                "line": row[8],
                "exception": row[9],
                "request_id": str(row[10]) if row[10] else None,
                "task_id": str(row[11]) if row[11] else None,
                "user_id": row[12],
                "metadata": row[13] or {},
                "created_at": row[14].isoformat() if row[14] else None,
            }

        except Exception as e:
            raise DatabaseError(f"Failed to get log by ID: {e}")
