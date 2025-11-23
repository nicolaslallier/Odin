"""Structured logging configuration for the Worker service.

This module configures structured logging for Celery workers with
JSON output for better log aggregation.
"""

from __future__ import annotations

import logging
import os
from typing import Any

# Import the structured logging from API (DRY principle)
from src.api.logging_config import (
    LoggerAdapter,
    configure_logging_with_db,
)
from src.api.logging_config import (
    get_logger as api_get_logger,
)


def configure_worker_logging(
    level: str = "INFO",
    use_json: bool = True,
    db_dsn: str | None = None,
) -> None:
    """Configure structured logging for Celery workers with database handler.

    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        use_json: Whether to use JSON formatting
        db_dsn: Optional PostgreSQL DSN for database logging
    """
    # Use the shared logging configuration with database support
    configure_logging_with_db(
        level=level,
        use_json=use_json,
        db_dsn=db_dsn,
        service_name="worker",
        db_min_level=os.environ.get("LOG_LEVEL_DB_MIN", "INFO"),
        db_buffer_size=int(os.environ.get("LOG_BUFFER_SIZE", "100")),
        db_buffer_timeout=float(os.environ.get("LOG_BUFFER_TIMEOUT", "5.0")),
    )

    # Additional Celery-specific configuration
    celery_logger = logging.getLogger("celery")
    celery_logger.setLevel(getattr(logging, level.upper(), logging.INFO))


def get_task_logger(
    name: str, task_id: str | None = None, **context: Any
) -> logging.Logger | LoggerAdapter:
    """Get a logger for Celery tasks with task context.

    Args:
        name: Logger name (usually __name__)
        task_id: Celery task ID
        **context: Additional context to add to all logs

    Returns:
        Logger or LoggerAdapter with context

    Example:
        >>> logger = get_task_logger(__name__, task_id=self.request.id)
        >>> logger.info("Processing task")
    """
    if task_id:
        context["task_id"] = task_id
    return api_get_logger(name, **context)
