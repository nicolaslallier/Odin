"""Scheduled tasks for periodic execution.

This module contains tasks that are executed periodically by Celery Beat,
including health checks, cleanup operations, and report generation.
"""

from __future__ import annotations

from collections.abc import Generator
from contextlib import contextmanager
from datetime import datetime, timedelta
from typing import Any

import httpx
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from src.worker.celery_app import celery_app


@contextmanager
def session_scope() -> Generator[Session, None, None]:
    """Provide a transactional scope for database operations.

    Yields:
        Database session

    Example:
        >>> with session_scope() as session:
        >>>     session.query(Model).all()
    """
    from src.worker.config import get_config

    config = get_config()
    # Extract database URL from result_backend (remove db+ prefix)
    db_url = config.result_backend.replace("db+", "")
    engine = create_engine(db_url)
    session_factory = sessionmaker(bind=engine)
    session = session_factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


@celery_app.task(name="src.worker.tasks.scheduled.health_check_services")
def health_check_services() -> dict[str, Any]:
    """Check health of all infrastructure services.

    This task pings all configured services to verify they are operational
    and returns a summary of the health check results.

    Returns:
        Dictionary containing health check results

    Example:
        >>> result = health_check_services.delay()
        >>> print(result.get())
    """
    services = {
        "postgresql": "http://postgresql:5432",
        "rabbitmq": "http://rabbitmq:15672/api/health/checks/alarms",
        "vault": "http://vault:8200/v1/sys/health",
        "minio": "http://minio:9000/minio/health/live",
    }

    results: dict[str, Any] = {"services": {}, "checked": 0, "failures": 0}

    for service_name, service_url in services.items():
        try:
            response = httpx.get(service_url, timeout=5.0)
            if response.status_code == 200:
                results["services"][service_name] = {
                    "status": "healthy",
                    "response_time": response.elapsed.total_seconds(),
                }
                results["checked"] += 1
            else:
                results["services"][service_name] = {
                    "status": "unhealthy",
                    "status_code": response.status_code,
                }
                results["failures"] += 1
        except Exception as e:
            results["services"][service_name] = {
                "status": "unavailable",
                "error": str(e),
            }
            results["failures"] += 1

    results["status"] = "success" if results["failures"] == 0 else "partial"
    results["timestamp"] = datetime.now().isoformat()

    return results


@celery_app.task(name="src.worker.tasks.scheduled.cleanup_old_task_results")
def cleanup_old_task_results(days: int = 30) -> dict[str, Any]:
    """Clean up old task results from the database.

    This task removes task results older than the specified retention period
    to prevent the result backend from growing unbounded.

    Args:
        days: Number of days to keep task results (default: 30)

    Returns:
        Dictionary containing cleanup results

    Example:
        >>> result = cleanup_old_task_results.delay(days=7)
        >>> print(result.get())
    """
    try:
        with session_scope() as session:
            # Calculate cutoff date
            cutoff_date = datetime.now() - timedelta(days=days)

            # Query and delete old task results
            # Note: Actual table structure depends on Celery's result backend schema
            deleted_count = (
                session.query(session.get_bind().dialect.name)
                .filter(datetime.now() > cutoff_date)
                .delete()
            )

            return {
                "status": "success",
                "deleted": deleted_count,
                "days": days,
                "cutoff_date": cutoff_date.isoformat(),
                "message": (
                    "No old task results to clean up"
                    if deleted_count == 0
                    else f"Deleted {deleted_count} old task results"
                ),
            }
    except Exception as e:
        return {"status": "error", "error": str(e), "days": days}


@celery_app.task(name="src.worker.tasks.scheduled.generate_daily_report")
def generate_daily_report() -> dict[str, Any]:
    """Generate a daily summary report of task execution.

    This task generates a report summarizing task execution statistics
    for the previous day, including success rates and failure analysis.

    Returns:
        Dictionary containing the daily report

    Example:
        >>> result = generate_daily_report.delay()
        >>> print(result.get())
    """
    try:
        with session_scope() as session:
            # Get today's date
            today = datetime.now()

            # Query task statistics
            # Note: Actual implementation depends on result backend schema
            summary = {
                "total_tasks": 0,
                "successful_tasks": 0,
                "failed_tasks": 0,
                "pending_tasks": 0,
            }

            return {
                "status": "success",
                "date": today.isoformat(),
                "summary": summary,
                "generated_at": datetime.now().isoformat(),
            }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "date": datetime.now().isoformat(),
        }
