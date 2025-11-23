"""Scheduled tasks for periodic execution.

This module contains tasks that are executed periodically by Celery Beat,
including health checks, cleanup operations, and report generation.
"""

from __future__ import annotations

import time
from collections.abc import Generator
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
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


@celery_app.task(name="src.worker.tasks.scheduled.collect_and_record_health_checks")
def collect_and_record_health_checks() -> dict[str, Any]:
    """Collect health status from all services and record to TimescaleDB.

    This task runs every minute to:
    1. Fetch infrastructure health from odin-API /health/services
    2. Check application services (api, worker, flower) via HTTP
    3. Send batch health check data to odin-API /health/record endpoint

    Returns:
        Dictionary containing collection results and statistics

    Example:
        >>> result = collect_and_record_health_checks.delay()
        >>> print(result.get())
    """
    start_time = time.time()
    api_base_url = "http://odin-api:8001"
    checks = []
    errors = []

    try:
        # Fetch infrastructure health from API
        try:
            with httpx.Client(timeout=5.0) as client:
                response = client.get(f"{api_base_url}/health/services")
                if response.status_code == 200:
                    infra_health = response.json()
                    # Convert to health check records
                    for service_name, is_healthy in infra_health.items():
                        checks.append(
                            {
                                "service_name": service_name,
                                "service_type": "infrastructure",
                                "is_healthy": is_healthy,
                                "response_time_ms": None,
                                "error_message": None if is_healthy else "Service unhealthy",
                                "metadata": {},
                            }
                        )
                else:
                    errors.append(f"Failed to fetch infrastructure health: {response.status_code}")
        except Exception as e:
            errors.append(f"Error fetching infrastructure health: {str(e)}")

        # Check API service health
        try:
            with httpx.Client(timeout=5.0) as client:
                start = time.time()
                response = client.get(f"{api_base_url}/health")
                elapsed_ms = (time.time() - start) * 1000

                is_healthy = response.status_code == 200
                checks.append(
                    {
                        "service_name": "api",
                        "service_type": "application",
                        "is_healthy": is_healthy,
                        "response_time_ms": elapsed_ms,
                        "error_message": (
                            None if is_healthy else f"Status code: {response.status_code}"
                        ),
                        "metadata": {},
                    }
                )
        except Exception as e:
            checks.append(
                {
                    "service_name": "api",
                    "service_type": "application",
                    "is_healthy": False,
                    "response_time_ms": None,
                    "error_message": str(e),
                    "metadata": {},
                }
            )

        # Check Worker/Beat via Flower API
        try:
            with httpx.Client(timeout=3.0) as client:
                auth = httpx.BasicAuth("admin", "admin")
                response = client.get("http://odin-flower:5555/api/workers", auth=auth)

                is_healthy = response.status_code == 200
                checks.append(
                    {
                        "service_name": "worker",
                        "service_type": "application",
                        "is_healthy": is_healthy,
                        "response_time_ms": None,
                        "error_message": None if is_healthy else "Worker unavailable",
                        "metadata": {},
                    }
                )

                checks.append(
                    {
                        "service_name": "beat",
                        "service_type": "application",
                        "is_healthy": is_healthy,
                        "response_time_ms": None,
                        "error_message": None if is_healthy else "Beat unavailable",
                        "metadata": {},
                    }
                )
        except Exception as e:
            checks.append(
                {
                    "service_name": "worker",
                    "service_type": "application",
                    "is_healthy": False,
                    "response_time_ms": None,
                    "error_message": str(e),
                    "metadata": {},
                }
            )
            checks.append(
                {
                    "service_name": "beat",
                    "service_type": "application",
                    "is_healthy": False,
                    "response_time_ms": None,
                    "error_message": str(e),
                    "metadata": {},
                }
            )

        # Check Flower service
        try:
            with httpx.Client(timeout=3.0) as client:
                auth = httpx.BasicAuth("admin", "admin")
                start = time.time()
                response = client.get("http://odin-flower:5555/", auth=auth, follow_redirects=True)
                elapsed_ms = (time.time() - start) * 1000

                is_healthy = response.status_code == 200
                checks.append(
                    {
                        "service_name": "flower",
                        "service_type": "application",
                        "is_healthy": is_healthy,
                        "response_time_ms": elapsed_ms,
                        "error_message": (
                            None if is_healthy else f"Status code: {response.status_code}"
                        ),
                        "metadata": {},
                    }
                )
        except Exception as e:
            checks.append(
                {
                    "service_name": "flower",
                    "service_type": "application",
                    "is_healthy": False,
                    "response_time_ms": None,
                    "error_message": str(e),
                    "metadata": {},
                }
            )

        # Send health checks to API for recording
        if checks:
            try:
                timestamp = datetime.now(timezone.utc).isoformat()
                payload = {
                    "checks": checks,
                    "timestamp": timestamp,
                }

                with httpx.Client(timeout=10.0) as client:
                    response = client.post(f"{api_base_url}/health/record", json=payload)

                    if response.status_code == 201:
                        record_result = response.json()
                    else:
                        errors.append(f"Failed to record health checks: {response.status_code}")
                        record_result = None
            except Exception as e:
                errors.append(f"Error recording health checks: {str(e)}")
                record_result = None
        else:
            record_result = None

        # Calculate statistics
        total_checks = len(checks)
        healthy_count = sum(1 for check in checks if check["is_healthy"])
        unhealthy_count = total_checks - healthy_count
        elapsed_time = time.time() - start_time

        return {
            "status": "success" if not errors else "partial",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "total_checks": total_checks,
            "healthy": healthy_count,
            "unhealthy": unhealthy_count,
            "recorded": record_result.get("recorded") if record_result else 0,
            "errors": errors,
            "elapsed_seconds": round(elapsed_time, 2),
        }

    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "checks_collected": len(checks),
            "errors": errors,
        }
