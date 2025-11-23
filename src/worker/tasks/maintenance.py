"""Maintenance tasks for system cleanup and health monitoring.

This module provides periodic maintenance tasks including log cleanup
and system health monitoring.
"""

from __future__ import annotations

import logging
import os
from datetime import datetime

from celery import Task

from src.worker.celery_app import get_celery_app

logger = logging.getLogger(__name__)
celery_app = get_celery_app()


@celery_app.task(name="maintenance.cleanup_old_logs", bind=True)
def cleanup_old_logs_task(self: Task, retention_days: int | None = None) -> dict[str, any]:
    """Clean up logs older than retention period.

    This task deletes old logs from the database to maintain retention policy
    and prevent database bloat.

    Args:
        self: Celery task instance
        retention_days: Number of days to retain logs (default: from env or 30)

    Returns:
        Dictionary with cleanup results

    Example:
        >>> result = cleanup_old_logs_task.apply_async()
        >>> print(result.get())
        {'deleted_count': 1234, 'retention_days': 30, 'timestamp': '...'}
    """
    # Get retention days from environment or use default
    if retention_days is None:
        retention_days = int(os.environ.get("LOG_RETENTION_DAYS", "30"))

    logger.info(f"Starting log cleanup task (retention: {retention_days} days)")

    try:
        # Import here to avoid circular dependencies
        import asyncio

        from sqlalchemy import text
        from sqlalchemy.ext.asyncio import create_async_engine

        # Get database connection from environment
        postgres_dsn = os.environ.get("POSTGRES_DSN")
        if not postgres_dsn:
            # Convert from Celery result backend format
            result_backend = os.environ.get("CELERY_RESULT_BACKEND", "")
            if result_backend.startswith("db+postgresql://"):
                postgres_dsn = result_backend.replace("db+postgresql://", "postgresql+asyncpg://")

        if not postgres_dsn:
            logger.error("No PostgreSQL DSN configured")
            return {
                "status": "error",
                "message": "No database connection configured",
                "deleted_count": 0,
                "retention_days": retention_days,
                "timestamp": datetime.utcnow().isoformat(),
            }

        # Run cleanup in async context
        async def run_cleanup():
            engine = create_async_engine(postgres_dsn, echo=False)
            try:
                async with engine.begin() as conn:
                    result = await conn.execute(
                        text("SELECT * FROM cleanup_old_logs(:retention_days)"),
                        {"retention_days": retention_days},
                    )
                    row = result.fetchone()
                    deleted_count = row[0] if row else 0
                    return deleted_count
            finally:
                await engine.dispose()

        # Execute cleanup
        deleted_count = asyncio.run(run_cleanup())

        logger.info(f"Log cleanup completed: {deleted_count} logs deleted")

        return {
            "status": "success",
            "deleted_count": deleted_count,
            "retention_days": retention_days,
            "timestamp": datetime.utcnow().isoformat(),
        }

    except Exception as e:
        logger.error(f"Log cleanup failed: {e}", exc_info=True)
        return {
            "status": "error",
            "message": str(e),
            "deleted_count": 0,
            "retention_days": retention_days,
            "timestamp": datetime.utcnow().isoformat(),
        }


@celery_app.task(name="maintenance.log_statistics", bind=True)
def log_statistics_task(self: Task) -> dict[str, any]:
    """Generate and log database statistics.

    This task collects statistics about log storage and system health.

    Args:
        self: Celery task instance

    Returns:
        Dictionary with statistics

    Example:
        >>> result = log_statistics_task.apply_async()
        >>> print(result.get())
        {'total_logs': 50000, 'table_size_mb': 125.5, ...}
    """
    logger.info("Collecting log statistics")

    try:
        import asyncio
        import os

        from sqlalchemy import text
        from sqlalchemy.ext.asyncio import create_async_engine

        # Get database connection
        postgres_dsn = os.environ.get("POSTGRES_DSN")
        if not postgres_dsn:
            result_backend = os.environ.get("CELERY_RESULT_BACKEND", "")
            if result_backend.startswith("db+postgresql://"):
                postgres_dsn = result_backend.replace("db+postgresql://", "postgresql+asyncpg://")

        if not postgres_dsn:
            return {"status": "error", "message": "No database connection configured"}

        async def get_stats():
            engine = create_async_engine(postgres_dsn, echo=False)
            try:
                async with engine.begin() as conn:
                    # Get total log count
                    result = await conn.execute(text("SELECT COUNT(*) FROM application_logs"))
                    total_logs = result.scalar()

                    # Get table size
                    result = await conn.execute(
                        text(
                            """
                            SELECT pg_size_pretty(pg_total_relation_size('application_logs'))
                        """
                        )
                    )
                    table_size = result.scalar()

                    # Get counts by level
                    result = await conn.execute(
                        text(
                            """
                            SELECT level, COUNT(*) as count
                            FROM application_logs
                            GROUP BY level
                        """
                        )
                    )
                    by_level = {row[0]: row[1] for row in result.fetchall()}

                    # Get oldest and newest log
                    result = await conn.execute(
                        text(
                            """
                            SELECT
                                MIN(timestamp) as oldest,
                                MAX(timestamp) as newest
                            FROM application_logs
                        """
                        )
                    )
                    row = result.fetchone()
                    oldest = row[0].isoformat() if row[0] else None
                    newest = row[1].isoformat() if row[1] else None

                    return {
                        "status": "success",
                        "total_logs": total_logs,
                        "table_size": table_size,
                        "by_level": by_level,
                        "oldest_log": oldest,
                        "newest_log": newest,
                        "timestamp": datetime.utcnow().isoformat(),
                    }
            finally:
                await engine.dispose()

        stats = asyncio.run(get_stats())
        logger.info(f"Log statistics: {stats['total_logs']} logs, size: {stats['table_size']}")
        return stats

    except Exception as e:
        logger.error(f"Failed to collect statistics: {e}", exc_info=True)
        return {
            "status": "error",
            "message": str(e),
            "timestamp": datetime.utcnow().isoformat(),
        }
